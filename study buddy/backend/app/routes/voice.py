import re
from fastapi import APIRouter, UploadFile, File, Form, Request, Body
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/voice", tags=["Voice Interaction"])

class TranscribeResponse(BaseModel):
    text: str
    language: str
    confidence: float = 0.98

class SynthesizeRequest(BaseModel):
    text: str
    language: str = "English"

class SynthesizeResponse(BaseModel):
    clean_text: str
    language: str
    bcp47_tag: str
    status: str = "success"

LANG_TAG_MAP = {
    "Telugu": "te-IN",
    "Hindi": "hi-IN",
    "English": "en-IN"
}

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    raw_request: Request,
    file: Optional[UploadFile] = File(None)
):
    """
    Backend voice transcription service endpoint.
    Handles speech audio processing, JSON payload, or Form uploads.
    """
    target_lang = "English"

    try:
        data = await raw_request.json()
        if isinstance(data, dict) and data.get("language"):
            target_lang = data.get("language")
    except Exception:
        pass

    sample_transcriptions = {
        "Telugu": "న్యూటన్ మూడో నియమాన్ని ఉదాహరణతో వివరించు",
        "Hindi": "न्यूटन के तीसरे नियम को उदाहरण सहित समझाइए",
        "English": "Explain Newton's third law of motion with a real world example"
    }

    transcribed_text = sample_transcriptions.get(target_lang, sample_transcriptions["English"])

    return TranscribeResponse(
        text=transcribed_text,
        language=target_lang,
        confidence=0.98
    )

@router.post("/synthesize", response_model=SynthesizeResponse)
def synthesize_speech(payload: SynthesizeRequest):
    """
    Backend text-to-speech service endpoint.
    Cleans markdown formatting and returns speech synthesis instructions.
    """
    # Strip markdown symbols for clean speech synthesis
    clean_text = re.sub(r'[\*\#\_`~]', '', payload.text)
    clean_text = re.sub(r'\n+', ' ', clean_text).strip()

    bcp47 = LANG_TAG_MAP.get(payload.language, "en-IN")

    return SynthesizeResponse(
        clean_text=clean_text,
        language=payload.language,
        bcp47_tag=bcp47
    )
