from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import shutil
import openai
import os
from pathlib import Path

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Create audio directory if it doesn't exist
AUDIO_DIR = Path("audio_files")
AUDIO_DIR.mkdir(exist_ok=True)

# Serve static files
app.mount("/audio", StaticFiles(directory="audio_files"), name="audio")

@app.post("/process-audio")
async def process_audio(file: UploadFile = File(...)):
    try:
        # Save the uploaded file
        temp_path = AUDIO_DIR / "input.wav"
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process with Whisper
        with open(temp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        
        # Get GPT response
        chat_completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant for rural India. Keep responses clear and concise."},
                {"role": "user", "content": transcript}
            ]
        )
        
        response_text = chat_completion.choices[0].message.content
        
        # Generate speech
        speech_file = AUDIO_DIR / "response.mp3"
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=response_text
        )
        response.stream_to_file(str(speech_file))
        
        return JSONResponse({
            "text": transcript,
            "response": response_text,
            "audio_url": "/audio/response.mp3"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup input file
        if temp_path.exists():
            temp_path.unlink()
