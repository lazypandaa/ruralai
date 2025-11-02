from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from openai import AzureOpenAI
import os
import requests
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import asyncio

app = FastAPI()

# MongoDB connection with working credentials
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://gramvani_user:GramVaani123!@firewall.jchsp.mongodb.net/gramvani?retryWrites=true&w=majority")
client_mongo = AsyncIOMotorClient(MONGO_URL)
db = client_mongo.gramvani
users_collection = db.user
user_queries_collection = db.user_queries

print("MongoDB connection initialized with gramvani_user")

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"

# CORS
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://lazypandaa.github.io",
    "https://eshwarkrishna.me",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Azure OpenAI
azure_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
)

# Models
class UserSignup(BaseModel):
    email: EmailStr
    password: str
    language: str
    location: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TextRequest(BaseModel):
    text: str
    language: str = "en"

class WeatherRequest(BaseModel):
    city: Optional[str] = None
    language: str = "en"

class CropPriceRequest(BaseModel):
    crop: str
    market: Optional[str] = None
    language: str = "en"

class SchemeRequest(BaseModel):
    topic: str
    language: str = "en"

class ReverseGeocodeRequest(BaseModel):
    latitude: float
    longitude: float

# Auth functions
def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user = await users_collection.find_one({"email": email})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except Exception as e:
        print(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

# Database initialization
async def init_db():
    try:
        # Test connection
        await client_mongo.admin.command('ping')
        print("MongoDB connection successful")
        
        # Create indexes
        await users_collection.create_index("email", unique=True)
        await user_queries_collection.create_index("user_email")
        
        # Create test user if not exists
        test_user = await users_collection.find_one({"email": "test@example.com"})
        if not test_user:
            hashed_password = get_password_hash("password123")
            await users_collection.insert_one({
                "email": "test@example.com",
                "password": hashed_password,
                "language": "en",
                "location": "Delhi, India",
                "created_at": datetime.utcnow()
            })
            print("Test user created")
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    await init_db()

# Routes
@app.get("/")
async def root():
    return {"message": "Gram Vaani API with MongoDB is running"}

@app.get("/health")
async def health():
    try:
        await client_mongo.admin.command('ping')
        user_count = await users_collection.count_documents({})
        test_user_exists = await users_collection.find_one({"email": "test@example.com"}) is not None
        
        return {
            "status": "healthy",
            "database": "connected",
            "users": user_count,
            "test_user_exists": test_user_exists
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

@app.get("/api/location")
async def get_location():
    try:
        url = "http://ipapi.co/json/"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if response.status_code == 200:
            return {
                "city": data.get("city", "Unknown"),
                "region": data.get("region", "Unknown"),
                "country": data.get("country_name", "Unknown"),
                "location": f"{data.get('city', 'Unknown')}, {data.get('region', 'Unknown')}"
            }
        else:
            return {"location": "Location not available"}
    except Exception as e:
        print(f"Location API error: {e}")
        return {"location": "Delhi, India"}

@app.post("/api/reverse-geocode")
async def reverse_geocode(request: ReverseGeocodeRequest):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={request.latitude}&lon={request.longitude}&zoom=18&addressdetails=1"
        
        headers = {
            'User-Agent': 'GramVaani-App/1.0 (contact@gramvaani.com)'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'address' in data:
                address_parts = data['address']
                
                village = address_parts.get('village', '')
                town = address_parts.get('town', '')
                city = address_parts.get('city', '')
                district = address_parts.get('state_district', '')
                state = address_parts.get('state', '')
                postcode = address_parts.get('postcode', '')
                
                address_components = []
                
                if village:
                    address_components.append(village)
                elif town:
                    address_components.append(town)
                elif city:
                    address_components.append(city)
                    
                if district and district not in address_components:
                    address_components.append(district)
                    
                if state:
                    address_components.append(state)
                    
                if postcode:
                    address_components.append(postcode)
                
                precise_address = ', '.join(filter(None, address_components))
                
                return {
                    "address": precise_address,
                    "coordinates": {
                        "latitude": request.latitude,
                        "longitude": request.longitude
                    }
                }
            else:
                return {"address": f"Coordinates: {request.latitude:.4f}, {request.longitude:.4f}"}
        else:
            return {"address": f"Coordinates: {request.latitude:.4f}, {request.longitude:.4f}"}
            
    except Exception as e:
        print(f"Reverse geocoding error: {e}")
        return {"address": f"Coordinates: {request.latitude:.4f}, {request.longitude:.4f}"}

@app.post("/api/signup", response_model=Token)
async def signup(user: UserSignup):
    try:
        existing_user = await users_collection.find_one({"email": user.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        hashed_password = get_password_hash(user.password)
        user_doc = {
            "email": user.email,
            "password": hashed_password,
            "language": user.language,
            "location": user.location,
            "created_at": datetime.utcnow()
        }
        
        await users_collection.insert_one(user_doc)
        
        access_token = create_access_token(data={"sub": user.email})
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/login", response_model=Token)
async def login(user: UserLogin):
    try:
        print(f"Login attempt for: {user.email}")
        db_user = await users_collection.find_one({"email": user.email})
        if not db_user:
            print(f"User not found: {user.email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        if not verify_password(user.password, db_user["password"]):
            print(f"Invalid password for: {user.email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        access_token = create_access_token(data={"sub": user.email})
        print(f"Login successful for: {user.email}")
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "email": current_user["email"],
        "language": current_user["language"],
        "location": current_user["location"]
    }

@app.post("/process-text")
async def process_text(request: TextRequest, current_user: dict = Depends(get_current_user)):
    try:
        user_location = current_user.get("location", "India")
        
        response = azure_client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt35"),
            messages=[
                {"role": "system", "content": f"You are Gram Vaani, AI Voice Assistant for Rural India. Help with farming, weather, crops, and government schemes. User is in {user_location}."},
                {"role": "user", "content": request.text}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        response_text = response.choices[0].message.content
        
        # Log query to MongoDB
        await user_queries_collection.insert_one({
            "user_email": current_user["email"],
            "query": request.text,
            "response": response_text,
            "timestamp": datetime.utcnow()
        })
        
        return JSONResponse({
            "response_text": response_text,
            "audio_data": None
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/weather")
async def get_weather(request: WeatherRequest, current_user: dict = Depends(get_current_user)):
    try:
        city = request.city or current_user.get("location", "Delhi").split(",")[0]
        
        api_key = os.getenv("OPENWEATHER_API_KEY", "99f42bfabc8ad962157251343277ea08")
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        res = requests.get(url)
        data = res.json()

        if res.status_code != 200:
            return JSONResponse({"error": "Weather data not found"}, status_code=400)

        weather_desc = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        
        response_text = f"Weather in {city}: {weather_desc}, temperature {temp}°C, humidity {humidity}%"
        
        return JSONResponse({"text": response_text, "audio_data": None})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/crop-prices")
async def get_crop_prices(request: CropPriceRequest, current_user: dict = Depends(get_current_user)):
    try:
        market = request.market or current_user.get("location", "Delhi").split(",")[0]
        
        # Simulate crop prices
        base_prices = {
            'wheat': 2000, 'rice': 2400, 'corn': 1600, 'barley': 1800,
            'sugarcane': 5000, 'cotton': 6000, 'soybean': 4400, 'mustard': 5600,
            'onion': 3000, 'potato': 1400, 'tomato': 3600, 'chili': 8000
        }
        
        price = base_prices.get(request.crop.lower(), 2500)
        response_text = f"Current price of {request.crop} in {market} market is ₹{price} per quintal"
        
        return JSONResponse({"text": response_text, "audio_data": None})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/gov-schemes")
async def get_gov_schemes(request: SchemeRequest, current_user: dict = Depends(get_current_user)):
    try:
        response = azure_client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt35"),
            messages=[
                {"role": "system", "content": "You are Gram Vaani, AI assistant for rural India. Provide information about government schemes for farmers in simple terms."},
                {"role": "user", "content": f"Tell me about government schemes related to {request.topic}"}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        response_text = response.choices[0].message.content
        
        return JSONResponse({"text": response_text, "audio_data": None})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))