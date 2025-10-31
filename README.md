# 🌾 Gram Vaani - AI Voice Assistant

## Quick Setup

### 1. Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup (New Terminal)
```bash
cd frontend
npm install
npm run dev
```

## Troubleshooting

### Error: `net::ERR_CONNECTION_REFUSED`
**Solution:** Backend server is not running
1. Open terminal in `backend` folder
2. Run: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
3. Wait for "Application startup complete"
4. Then start frontend

### Error: `password cannot be longer than 72 bytes`
**Solution:** Use shorter passwords (under 72 characters)

### Error: MongoDB connection failed
**Solution:** Check internet connection and MongoDB Atlas access

## Required Services
- MongoDB Atlas (cloud database)
- Azure OpenAI API
- Azure Speech Services
- OpenWeather API

## Default URLs
- Frontend: http://localhost:5173
- Backend: http://localhost:8000