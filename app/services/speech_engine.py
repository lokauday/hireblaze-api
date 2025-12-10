import openai
from app.core.config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY


async def transcribe_audio_chunk(audio_bytes: bytes):
    """
    Accepts short audio chunks and returns transcribed text using Whisper.
    """
    transcript = openai.audio.transcriptions.create(
        file=audio_bytes,
        model="gpt-4o-transcribe"
    )

    return transcript.text
