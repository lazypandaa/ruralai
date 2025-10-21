from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from openai import AzureOpenAI, OpenAI
import os
import tempfile

app = FastAPI()

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

# Initialize OpenAI client for Whisper
openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    print("WARNING: OPENAI_API_KEY not found in environment variables")
    client = None
else:
    client = OpenAI(api_key=openai_key)



@app.post("/process-audio")
async def process_audio(file: UploadFile = File(...)):
    temp_file = None
    try:
        # Save audio to temporary file
        content = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        print(f"Audio file received: {len(content)} bytes")

        # Speech to text using OpenAI Whisper
        transcript = None
        if client:
            try:
                with open(temp_file_path, "rb") as audio_file:
                    # Set file name for proper format detection
                    audio_file.name = "audio.webm"
                    response = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                    transcript = response.text
                    print(f"Whisper transcription successful: {transcript}")
            except Exception as speech_error:
                print(f"Whisper error: {speech_error}")
                transcript = "Could not understand the audio. Please speak clearly."
        else:
            print("OpenAI client not available - no API key")
            transcript = "Speech recognition unavailable. Please use text input."

        # Get Azure OpenAI response only if we have valid transcript
        if transcript and "Could not understand" not in transcript and "unavailable" not in transcript:
            messages = [
                {"role": "system", "content": "You are a helpful assistant for rural India focused on farming, weather, crops, and government schemes. Respond in simple, clear language."},
                {"role": "user", "content": transcript}
            ]
            try:
                response = azure_client.chat.completions.create(
                    model=azure_deployment,
                    messages=messages,
                    max_tokens=4096,
                    temperature=0.7
                )
                response_text = response.choices[0].message.content
                print(f"Azure OpenAI response generated successfully")
            except Exception as azure_error:
                print(f"Azure OpenAI error: {azure_error}")
                response_text = "I'm here to help you with farming, weather, and government schemes. Please try again or use text input."
        else:
            response_text = "I couldn't understand your audio. Please try speaking more clearly or use the text input option."

        return JSONResponse({
            "transcript": transcript,
            "response_text": response_text,
            "audio_url": None
        })

    except Exception as e:
        print(f"General error: {e}")
        return JSONResponse({
            "transcript": "Audio processing failed",
            "response_text": "I'm having trouble processing your audio. Please try the text input instead.",
            "audio_url": None
        })
    finally:
        # Cleanup temporary file
        if temp_file and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

class TextRequest(BaseModel):
    text: str

@app.post("/process-text")
async def process_text(request: TextRequest):
    try:
        # Get Azure OpenAI response
        messages = [
            {"role": "system", "content": "You are a helpful assistant for rural India focused on farming, weather, crops, and government schemes. Respond in simple, clear language."},
            {"role": "user", "content": request.text}
        ]
        response = azure_client.chat.completions.create(
            model=azure_deployment,
            messages=messages,
            max_tokens=4096,
            temperature=0.7
        )
        response_text = response.choices[0].message.content
        print(f"Text processing successful for: {request.text}")

        return JSONResponse(response_text)

    except Exception as e:
        print(f"Text processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
