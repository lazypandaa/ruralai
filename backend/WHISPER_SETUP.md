# OpenAI Whisper Speech Recognition Setup

## 1. Get OpenAI API Key
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Create account and get API key
3. Ensure you have credits for API usage

## 2. Set up environment variables
```bash
export OPENAI_API_KEY="your_openai_api_key_here"
export GEMINI_API_KEY="your_gemini_api_key_here"
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
- Multi-language support (Hindi, English, regional dialects)
- High accuracy speech recognition
- Automatic language detection
- Handles various audio formats