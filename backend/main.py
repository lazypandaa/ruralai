from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from openai import AzureOpenAI
import os
import tempfile
import requests
import azure.cognitiveservices.speech as speechsdk
import base64
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
from typing import Optional

app = FastAPI()

# MongoDB connection with working credentials
MONGO_URL = "mongodb+srv://gramvani_user:GramVaani123!@firewall.jchsp.mongodb.net/gramvani?retryWrites=true&w=majority"
client_mongo = AsyncIOMotorClient(MONGO_URL)
db = client_mongo.gramvani
users_collection = db.user
user_queries_collection = db.user_queries

print("MongoDB connection initialized with gramvani_user")

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
SECRET_KEY = "your-secret-key-here-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Azure OpenAI client
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://azadj-mh00wimr-eastus2.cognitiveservices.azure.com/")
azure_api_key = os.getenv("AZURE_OPENAI_API_KEY", "CAeNSw3Kjc9b3CzNcyDOaNGCaStBqL9dmg1j9cU4RIVqNILKSMnVJQQJ99BJACHYHv6XJ3w3AAAAACOG6dVR")
azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt35")
azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

azure_client = AzureOpenAI(
    azure_endpoint=azure_endpoint,
    api_key=azure_api_key,
    api_version=azure_api_version
)

client = azure_client  # alias

# ---------------------- AUTH MODELS ----------------------
class UserSignup(BaseModel):
    email: EmailStr
    password: str
    language: str
    location: str
    coordinates: Optional[dict] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class LocationRequest(BaseModel):
    ip: Optional[str] = None

class ReverseGeocodeRequest(BaseModel):
    latitude: float
    longitude: float

class ProfileUpdate(BaseModel):
    email: EmailStr
    language: str
    location: str

class QueryLog(BaseModel):
    query: str
    response: Optional[str] = None
    type: str = "general"

# ---------------------- LANGUAGE MAPPING ----------------------
def get_language_name(lang_code):
    language_map = {
        "en": "English",
        "hi": "Hindi (हिंदी)",
        "mr": "Marathi (मराठी)", 
        "bn": "Bengali (বাংলা)",
        "ta": "Tamil (தமிழ்)",
        "te": "Telugu (తెలుగు)"
    }
    return language_map.get(lang_code, "English")

# ---------------------- AUTH FUNCTIONS ----------------------
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    # Truncate password to 72 bytes for bcrypt compatibility
    if len(password.encode('utf-8')) > 72:
        password = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await users_collection.find_one({"email": email})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.PyJWTError as e:
        print(f"JWT error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

# ---------------------- LOCATION API ----------------------
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
        return {"location": "Location not available"}

@app.post("/api/reverse-geocode")
async def reverse_geocode(request: ReverseGeocodeRequest):
    try:
        # Using OpenStreetMap Nominatim for reverse geocoding (free service)
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={request.latitude}&lon={request.longitude}&zoom=18&addressdetails=1"
        
        headers = {
            'User-Agent': 'GramVaani-App/1.0 (contact@gramvaani.com)'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'address' in data:
                address_parts = data['address']
                
                # Extract relevant address components
                village = address_parts.get('village', '')
                town = address_parts.get('town', '')
                city = address_parts.get('city', '')
                district = address_parts.get('state_district', '')
                state = address_parts.get('state', '')
                country = address_parts.get('country', '')
                postcode = address_parts.get('postcode', '')
                
                # Build a comprehensive address
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
                    },
                    "details": {
                        "village": village,
                        "town": town,
                        "city": city,
                        "district": district,
                        "state": state,
                        "country": country,
                        "postcode": postcode
                    }
                }
            else:
                return {"address": f"Coordinates: {request.latitude:.4f}, {request.longitude:.4f}"}
        else:
            return {"address": f"Coordinates: {request.latitude:.4f}, {request.longitude:.4f}"}
            
    except Exception as e:
        print(f"Reverse geocoding error: {e}")
        return {"address": f"Coordinates: {request.latitude:.4f}, {request.longitude:.4f}"}

# ---------------------- AUTH ENDPOINTS ----------------------
@app.post("/api/signup", response_model=Token)
async def signup(user: UserSignup):
    try:
        print(f"Signup attempt for: {user.email}")
        
        # Check if user already exists
        existing_user = await users_collection.find_one({"email": user.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Simple approach - just try to insert, handle duplicate error
        hashed_password = get_password_hash(user.password)
        user_doc = {
            "email": user.email,
            "password": hashed_password,
            "language": user.language,
            "location": user.location,
            "coordinates": user.coordinates,
            "created_at": datetime.utcnow()
        }
        
        print(f"Inserting user document: {user.email}")
        result = await users_collection.insert_one(user_doc)
        print(f"User inserted with ID: {result.inserted_id}")
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        print(f"Signup successful for: {user.email}")
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        error_msg = str(e)
        print(f"Signup error details: {type(e).__name__}: {error_msg}")
        
        # Handle duplicate email
        if "duplicate key" in error_msg.lower() or "11000" in error_msg:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        raise HTTPException(status_code=500, detail=f"Registration failed: {error_msg}")

@app.post("/api/login", response_model=Token)
async def login(user: UserLogin):
    try:
        # Find user
        db_user = await users_collection.find_one({"email": user.email})
        if not db_user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify password with error handling
        try:
            password_valid = verify_password(user.password, db_user["password"])
        except Exception as pwd_error:
            print(f"Password verification error: {pwd_error}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
        if not password_valid:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.get("/api/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "email": current_user["email"],
        "language": current_user["language"],
        "location": current_user["location"]
    }

@app.put("/api/profile")
async def update_profile(profile_data: ProfileUpdate, current_user: dict = Depends(get_current_user)):
    try:
        await users_collection.update_one(
            {"email": current_user["email"]},
            {"$set": {
                "email": profile_data.email,
                "language": profile_data.language,
                "location": profile_data.location,
                "updated_at": datetime.utcnow()
            }}
        )
        return {"message": "Profile updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update profile")

@app.post("/api/log-query")
async def log_query(query_data: QueryLog, current_user: dict = Depends(get_current_user)):
    try:
        query_doc = {
            "user_email": current_user["email"],
            "query": query_data.query,
            "response": query_data.response,
            "type": query_data.type,
            "timestamp": datetime.utcnow()
        }
        await user_queries_collection.insert_one(query_doc)
        return {"message": "Query logged successfully"}
    except Exception as e:
        print(f"Query logging error: {e}")
        return {"message": "Query logging failed"}

@app.get("/api/user-queries")
async def get_user_queries(current_user: dict = Depends(get_current_user)):
    try:
        queries = await user_queries_collection.find(
            {"user_email": current_user["email"]}
        ).sort("timestamp", -1).limit(50).to_list(50)
        
        # Convert ObjectId to string for JSON serialization
        for query in queries:
            query["_id"] = str(query["_id"])
            
        return {"queries": queries}
    except Exception as e:
        print(f"Fetch queries error: {e}")
        return {"queries": []}

# Temporary in-memory storage as fallback
temp_users = {}

# Test endpoints
@app.post("/api/test-signup")
async def test_signup(user: UserSignup):
    try:
        print(f"Test signup for: {user.email}")
        if user.email in temp_users:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        temp_users[user.email] = {
            "email": user.email,
            "password": get_password_hash(user.password),
            "language": user.language,
            "location": user.location
        }
        
        access_token = create_access_token(data={"sub": user.email})
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        print(f"Test signup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/test-login")
async def test_login(user: UserLogin):
    try:
        if user.email not in temp_users:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        stored_user = temp_users[user.email]
        if not verify_password(user.password, stored_user["password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        access_token = create_access_token(data={"sub": user.email})
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        print(f"Test login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/test-me")
async def test_get_me(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None or email not in temp_users:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = temp_users[email]
        return {
            "email": user["email"],
            "language": user["language"],
            "location": user["location"]
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/api/test-db")
async def test_database_access():
    try:
        test_results = {}
        
        # Test current connection
        try:
            await db.command("ping")
            test_results["current_connection"] = "SUCCESS"
            
            # Test insert operation
            test_doc = {"test": "data", "timestamp": datetime.utcnow()}
            result = await users_collection.insert_one(test_doc)
            test_results["insert_test"] = f"SUCCESS - ID: {result.inserted_id}"
            
            # Clean up test document
            await users_collection.delete_one({"_id": result.inserted_id})
            test_results["cleanup"] = "SUCCESS"
            
        except Exception as e:
            test_results["current_connection"] = f"FAILED: {str(e)}"
        
        return test_results
    except Exception as e:
        return {"error": str(e)}

# Azure Speech Services configuration
speech_config = speechsdk.SpeechConfig(
    subscription="AcO2p9Y3cCtDKiEh3DVKM9iAuQdwwqnKK4yzI368bGqPh3TO6vLEJQQJ99BJACYeBjFXJ3w3AAAYACOGKndq",
    region="eastus"
)

# ---------------------- AUDIO PROCESSING ----------------------
@app.post("/process-audio")
async def process_audio(file: UploadFile = File(...), language: str = "en", current_user: dict = Depends(get_current_user)):
    temp_file = None
    try:
        # Save audio to temporary file
        content = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        print(f"Audio file received: {len(content)} bytes, saved as: {temp_file_path}")

        # Speech to text using Azure Whisper deployment
        transcript = None
        try:
            with open(temp_file_path, "rb") as audio_file:
                # Map language codes to Whisper language codes
                whisper_lang_map = {
                    'hi': 'hi',  # Hindi
                    'mr': 'mr',  # Marathi  
                    'bn': 'bn',  # Bengali
                    'ta': 'ta',  # Tamil
                    'te': 'te'   # Telugu
                }
                whisper_language = whisper_lang_map.get(language) if language != 'en' else None
                
                response = azure_client.audio.transcriptions.create(
                    model="whisper",
                    file=audio_file,
                    language=whisper_language
                )
                transcript = response.text
                print(f"Azure Whisper transcription successful: {transcript}")
        except Exception as speech_error:
            print(f"Azure Whisper error: {speech_error}")
            transcript = "Could not understand the audio. Please speak clearly."

        # Get Azure OpenAI response only if we have valid transcript
        if transcript and "Could not understand" not in transcript:
            user_location = current_user.get("location", "India")
            
            # For non-English languages, use translation approach
            if language != 'en':
                # Step 1: Translate user input to English
                translate_to_english = azure_client.chat.completions.create(
                    model=azure_deployment,
                    messages=[
                        {"role": "system", "content": "Translate the following text to English. Only provide the translation, nothing else."},
                        {"role": "user", "content": transcript}
                    ],
                    max_tokens=500,
                    temperature=0.3
                )
                english_text = translate_to_english.choices[0].message.content.strip()
                
                # Step 2: Get response in English
                english_response = azure_client.chat.completions.create(
                    model=azure_deployment,
                    messages=[
                        {"role": "system", "content": f"You are Gram Vaani, AI Voice Assistant for Rural India. You help with farming, weather, crops, and government schemes. The user is located in {user_location}. Provide helpful, location-specific advice."},
                        {"role": "user", "content": english_text}
                    ],
                    max_tokens=1000,
                    temperature=0.7
                )
                english_answer = english_response.choices[0].message.content
                
                # Step 3: Translate response to target language with specific script instructions
                if language == 'hi':
                    translate_instruction = "Translate the following English text to Hindi using Devanagari script only (हिंदी). Do NOT use Arabic/Urdu script. Only provide the Hindi translation in Devanagari script."
                elif language == 'te':
                    translate_instruction = "Translate the following English text to Telugu using Telugu script only (తెలుగు). Only provide the Telugu translation."
                else:
                    language_name = get_language_name(language)
                    translate_instruction = f"Translate the following English text to {language_name}. Use proper native script. Only provide the translation, nothing else."
                    
                translate_response = azure_client.chat.completions.create(
                    model=azure_deployment,
                    messages=[
                        {"role": "system", "content": translate_instruction},
                        {"role": "user", "content": english_answer}
                    ],
                    max_tokens=1000,
                    temperature=0.3
                )
                response_text = translate_response.choices[0].message.content.strip()
            else:
                # For English, direct response
                messages = [
                    {"role": "system", "content": f"You are Gram Vaani, AI Voice Assistant for Rural India. You help with farming, weather, crops, and government schemes. The user is located in {user_location}. Provide helpful, location-specific advice."},
                    {"role": "user", "content": transcript}
                ]
                response = azure_client.chat.completions.create(
                    model=azure_deployment,
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7
                )
                response_text = response.choices[0].message.content
            try:
                print(f"Azure OpenAI response generated successfully")
                
                # Log the query
                await log_user_query(current_user["email"], transcript, response_text, "voice")
            except Exception as azure_error:
                print(f"Azure OpenAI error: {azure_error}")
                response_text = "I'm here to help you with farming, weather, and government schemes. Please try again."
        else:
            response_text = "I couldn't understand your audio. Please try speaking more clearly or use the text input option."
            
            # Log failed audio query
            await log_user_query(current_user["email"], "Audio processing failed", response_text, "voice")

        # Generate TTS audio
        audio_data = None
        try:
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
            result = synthesizer.speak_text_async(response_text).get()
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_data = base64.b64encode(result.audio_data).decode('utf-8')
        except Exception as tts_error:
            print(f"TTS error: {tts_error}")

        return JSONResponse({
            "transcript": transcript,
            "response_text": response_text,
            "audio_data": audio_data
        })

    except Exception as e:
        print(f"General error: {e}")
        return JSONResponse({
            "transcript": "Audio processing failed",
            "response_text": "I'm having trouble processing your audio. Please try again later.",
            "audio_url": None
        })
    finally:
        if temp_file and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


# ---------------------- TEXT PROCESSING ----------------------
class TextRequest(BaseModel):
    text: str
    language: str = "en"

@app.post("/process-text")
async def process_text(request: TextRequest, current_user: dict = Depends(get_current_user)):
    try:
        user_location = current_user.get("location", "India")
        
        # For non-English languages, use translation approach
        if request.language != 'en':
            # Step 1: Translate user input to English
            translate_to_english = azure_client.chat.completions.create(
                model=azure_deployment,
                messages=[
                    {"role": "system", "content": "Translate the following text to English. Only provide the translation, nothing else."},
                    {"role": "user", "content": request.text}
                ],
                max_tokens=500,
                temperature=0.3
            )
            english_text = translate_to_english.choices[0].message.content.strip()
            
            # Step 2: Get response in English
            english_response = azure_client.chat.completions.create(
                model=azure_deployment,
                messages=[
                    {"role": "system", "content": f"You are Gram Vaani, AI Voice Assistant for Rural India. You help with farming, weather, crops, and government schemes. The user is located in {user_location}. Provide helpful, location-specific advice."},
                    {"role": "user", "content": english_text}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            english_answer = english_response.choices[0].message.content
            
            # Step 3: Translate response to target language with specific script instructions
            if request.language == 'hi':
                translate_instruction = "Translate the following English text to Hindi using Devanagari script only (हिंदी). Do NOT use Arabic/Urdu script. Only provide the Hindi translation in Devanagari script."
            elif request.language == 'te':
                translate_instruction = "Translate the following English text to Telugu using Telugu script only (తెలుగు). Only provide the Telugu translation."
            else:
                language_name = get_language_name(request.language)
                translate_instruction = f"Translate the following English text to {language_name}. Use proper native script. Only provide the translation, nothing else."
                
            translate_response = azure_client.chat.completions.create(
                model=azure_deployment,
                messages=[
                    {"role": "system", "content": translate_instruction},
                    {"role": "user", "content": english_answer}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            response_text = translate_response.choices[0].message.content.strip()
        else:
            # For English, direct response
            messages = [
                {"role": "system", "content": f"You are Gram Vaani, AI Voice Assistant for Rural India. You help with farming, weather, crops, and government schemes. The user is located in {user_location}. Provide helpful, location-specific advice."},
                {"role": "user", "content": request.text}
            ]
            response = azure_client.chat.completions.create(
                model=azure_deployment,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            response_text = response.choices[0].message.content
        
        print(f"Text processing successful for: {request.text}")
        
        # Log the query
        await log_user_query(current_user["email"], request.text, response_text, "text")

        # Generate TTS audio
        audio_data = None
        try:
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
            result = synthesizer.speak_text_async(response_text).get()
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_data = base64.b64encode(result.audio_data).decode('utf-8')
        except Exception as tts_error:
            print(f"TTS error: {tts_error}")

        return JSONResponse({
            "response_text": response_text,
            "audio_data": audio_data
        })

    except Exception as e:
        print(f"Text processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ---------------------- WEATHER INFORMATION ----------------------
class WeatherRequest(BaseModel):
    city: str
    language: str = "en"

@app.post("/api/weather")
async def get_weather(request: WeatherRequest, current_user: dict = Depends(get_current_user)):
    try:
        api_key = os.getenv("OPENWEATHER_API_KEY", "99f42bfabc8ad962157251343277ea08")
        url = f"http://api.openweathermap.org/data/2.5/weather?q={request.city}&appid={api_key}&units=metric&lang={request.language}"
        res = requests.get(url)
        data = res.json()

        if res.status_code != 200:
            return JSONResponse({"error": data.get("message", "Weather data not found")}, status_code=400)

        weather_desc = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        response_text = f"The current weather in {request.city} is {weather_desc} with a temperature of {temp}°C and humidity {humidity}%."
        
        # Log the query
        await log_user_query(current_user["email"], f"Weather for {request.city}", response_text, "weather")
        
        # Generate TTS audio
        audio_data = None
        try:
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
            result = synthesizer.speak_text_async(response_text).get()
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_data = base64.b64encode(result.audio_data).decode('utf-8')
        except Exception as tts_error:
            print(f"TTS error: {tts_error}")
        
        return JSONResponse({"text": response_text, "audio_data": audio_data})
    except Exception as e:
        print(f"Weather API error: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch weather right now.")


# ---------------------- CROP PRICES ----------------------
class CropPriceRequest(BaseModel):
    crop: str
    market: str = "Delhi"
    language: str = "en"

@app.post("/api/crop-prices")
async def get_crop_prices(request: CropPriceRequest, current_user: dict = Depends(get_current_user)):
    try:
        # Simulated response
        response_text = f"The latest price for {request.crop} in {request.market} is ₹{round(2500 + hash(request.crop) % 500)} per quintal."
        
        # Log the query
        await log_user_query(current_user["email"], f"Price for {request.crop}", response_text, "crop")
        
        # Generate TTS audio
        audio_data = None
        try:
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
            result = synthesizer.speak_text_async(response_text).get()
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_data = base64.b64encode(result.audio_data).decode('utf-8')
        except Exception as tts_error:
            print(f"TTS error: {tts_error}")
        
        return JSONResponse({"text": response_text, "audio_data": audio_data})
    except Exception as e:
        print(f"Crop API error: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch crop prices right now.")


# ---------------------- GOVERNMENT SCHEMES ----------------------
class SchemeRequest(BaseModel):
    topic: str
    language: str = "en"

@app.post("/api/gov-schemes")
async def get_gov_schemes(request: SchemeRequest, current_user: dict = Depends(get_current_user)):
    try:
        language_name = get_language_name(request.language)
        messages = [
            {"role": "system", "content": f"You are Gram Vaani, AI Voice Assistant for Rural India. You are professional in providing information in efficient and effective manner for the rural area people. Provide info about government schemes related to agriculture in simple terms. IMPORTANT: Respond ONLY in {language_name}. Do not use any other language or script."},
            {"role": "user", "content": f"Tell me about government schemes related to {request.topic}."}
        ]
        response = azure_client.chat.completions.create(
            model=azure_deployment,
            messages=messages,
            max_tokens=1024,
            temperature=0.7
        )
        summary = response.choices[0].message.content
        
        # Log the query
        await log_user_query(current_user["email"], f"Government schemes for {request.topic}", summary, "schemes")
        
        # Generate TTS audio
        audio_data = None
        try:
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
            result = synthesizer.speak_text_async(summary).get()
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_data = base64.b64encode(result.audio_data).decode('utf-8')
        except Exception as tts_error:
            print(f"TTS error: {tts_error}")
        
        return JSONResponse({"text": summary, "audio_data": audio_data})
    except Exception as e:
        print(f"Gov scheme error: {e}")
        raise HTTPException(status_code=500, detail="Unable to fetch government schemes right now.")

# Helper function to log queries
async def log_user_query(user_email: str, query: str, response: str = None, query_type: str = "general"):
    try:
        query_doc = {
            "user_email": user_email,
            "query": query,
            "response": response,
            "type": query_type,
            "timestamp": datetime.utcnow()
        }
        await user_queries_collection.insert_one(query_doc)
    except Exception as e:
        print(f"Auto query logging error: {e}")