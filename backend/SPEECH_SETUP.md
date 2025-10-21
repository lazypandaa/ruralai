# Google Cloud Speech-to-Text Setup

## 1. Enable Google Cloud Speech-to-Text API
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Speech-to-Text API
4. Create a service account key (JSON format)

## 2. Set up authentication
```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"
export GEMINI_API_KEY="your_gemini_api_key"
```

## 3. Install dependencies
```bash
pip install -r requirements.txt
```

## 4. Run the server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Features
- Multi-language support (English, Hindi, Telugu, Punjabi, Bengali)
- Better accuracy than basic speech recognition
- Handles various audio formats
- Automatic punctuation