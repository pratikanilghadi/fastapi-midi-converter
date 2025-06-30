from pydantic import BaseModel, HttpUrl, Dict, Any
from typing import Optional

class AudioToMidiRequest(BaseModel):
    audio_download_url: HttpUrl
    midi_upload_url: HttpUrl
    audio_file_name: str

class ProcessingResponse(BaseModel):
    status: str
    message: str
    processing_info: Optional[Dict[str,Any]] = None

class ProcessingStatus(BaseModel):
    status: str
    progress: str
    message: str
    audio_info: Optional[dict] = None
    midi_info: Optional[dict] = None
    error_details: Optional[str] = None