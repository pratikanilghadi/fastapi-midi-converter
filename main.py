from fastapi import FastAPI, HTTPException, BackgroundTasks
import logging
import uuid
from typing import Dict

from model import AudioToMidiRequest, ProcessingResponse, ProcessingStatus
from functionality import validate_audio_download_url, validate_midi_upload_url, process_audio_to_midi

app = FastAPI(title="Audio to Midi Converter", description="Convert audio files to MIDI using the Basic Pitch conversion model")
logging.basicConfig(level=logging.INFO)
logger =  logging.getLogger(__name__)

SUPPORTED_AUDIO_FORMATS = {'.wav', '.mp3', '.flac', '.m4a', '.ogg', '.aac'}

processing_status:Dict = Dict()

@app.post("/process/audio-to-midi", response_model=dict)
async def convert_audio_to_midi(
    request: AudioToMidiRequest,
    background_tasks: BackgroundTasks
):
    processing_id = str(uuid.uuid4())
    processing_status[processing_id] = ProcessingStatus(
        status='initiated',
        progress=0,
        message="Audio to MIDI conversion initiated"
    )

    try:
        await validate_audio_download_url(request.audio_download_url)
        await validate_midi_upload_url(request.midi_upload_url)

        background_tasks.add_task(
            process_audio_to_midi,
            processing_id,
            request
        )

        return {
            "processing_id": processing_id,
            "status": "accepted",
            "message": "Audio to MIDI converson started",
            "estimated_time": "This may take 1-5 minutes depending on the compute available and length of the audio file"
        }

    except Exception as e:
        processing_status[processing_id].status = "failed"
        processing_status[processing_id].message = f"Failed to initiate: {str(e)}"
        logger.error(f"Error intiating audio to MIDI conversions: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))