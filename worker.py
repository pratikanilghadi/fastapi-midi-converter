import httpx
import logging
import tempfile
import os
import shutil
from pathlib import Path

from basic_pitch.inference import predict_and_save
from basic_pitch import ICASSP_2022_MODEL_PATH

from model import ProcessingRequest, StatusUpdateRequest
from config import settings

# Configure logger
logger = logging.getLogger(__name__)

SUPPORTED_AUDIO_FORMATS = {'.wav', '.mp3', '.flac', '.m4a', '.ogg', '.aac'}

async def update_status_api(job_id: str, payload: StatusUpdateRequest):
    """Sends a status update to the configured dynamic callback URL."""
    # Construct the full dynamic callback URL
    callback_url = f"{str(settings.POLYGEN_BACKEND_URL).rstrip('/')}/api/users/jobs/{job_id}/callback"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                callback_url,
                json=payload.model_dump(by_alias=True),
                timeout=10.0
            )
            response.raise_for_status()
            logger.info(f"Successfully sent status '{payload.status}' for job {payload.python_job_id} to {callback_url}")
    except httpx.RequestError as e:
        logger.error(f"Failed to send status update for job {payload.python_job_id}: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending status update for job {payload.python_job_id}: {e}")


async def run_audio_to_midi_job(request: ProcessingRequest):
    """
    The main background task function to process an audio-to-MIDI conversion job.
    """
    temp_dir = None
    job_id = request.job_id
    logger.info(f"Starting job: {job_id}")

    # A helper to create and send status updates, now passing job_id to the API call
    async def send_update(status, message, progress, size=None):
        payload = StatusUpdateRequest(
            user_id=request.user_id,
            file_id=request.metadata.original_file_id,
            status=status,
            progress=progress,
            message=message,
            size=size,
            python_job_id=job_id,
        )
        await update_status_api(job_id, payload)

    try:
        temp_dir = tempfile.mkdtemp(prefix=f"job_{job_id}_")

        # 1. Download audio file
        await send_update("processing", "Downloading audio file...", 10)
        audio_file_path = await download_file(str(request.input_file_url), temp_dir, request.metadata.file_name)

        # 2. Convert to MIDI
        await send_update("processing", "Converting audio to MIDI...", 50)
        midi_file_path = await convert_to_midi(audio_file_path, temp_dir, job_id)

        # 3. Upload MIDI file
        await send_update("processing", "Uploading converted MIDI file...", 90)
        midi_file_size = os.path.getsize(midi_file_path)
        await upload_file(midi_file_path, str(request.output_file_url))

        # 4. Final success update
        await send_update("completed", "Processing completed successfully.", 100, size=midi_file_size)
        logger.info(f"Job {job_id} completed successfully.")

    except Exception as e:
        # Use only the exception message for the callback to avoid overly technical details
        failure_message = str(e)
        # Log the full traceback for debugging
        logger.error(f"Job {job_id} failed: {failure_message}", exc_info=True)
        await send_update("failed", failure_message, 0)

    finally:
        # Cleanup temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")

# The rest of worker.py (download_file, convert_to_midi, upload_file) remains unchanged.
# ... (omitted for brevity) ...

async def download_file(download_url: str, temp_dir: str, file_name: str) -> str:
    """Downloads a file from a URL into a temporary directory."""
    file_extension = Path(file_name).suffix.lower()
    if file_extension not in SUPPORTED_AUDIO_FORMATS:
        raise ValueError(f"Unsupported audio format: {file_extension}")

    audio_file_path = os.path.join(temp_dir, f"input_audio{file_extension}")
    
    async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
        response = await client.get(download_url)
        response.raise_for_status()
        with open(audio_file_path, 'wb') as f:
            f.write(response.content)
    
    logger.info(f"Downloaded file to {audio_file_path}")
    return audio_file_path


async def convert_to_midi(audio_path: str, temp_dir: str, job_id: str) -> str:
    """Converts the downloaded audio file to MIDI using basic-pitch."""
    try:
        output_dir = os.path.join(temp_dir, "midi_output")
        os.makedirs(output_dir, exist_ok=True)
        predict_and_save(
            audio_path_list=[audio_path],
            output_directory=output_dir,
            save_midi=True,
            sonify_midi=False,
            save_model_outputs=False,
            save_notes=False,
            model_or_model_path=ICASSP_2022_MODEL_PATH
        )

        midi_files = list(Path(output_dir).glob("*.mid"))
        if not midi_files:
            raise Exception("No MIDI file was generated by basic_pitch")
        
        midi_file_path = str(midi_files[0])
        logger.info(f"MIDI file generated for job {job_id}: {midi_file_path}")
        return midi_file_path

    except Exception as e:
        logger.error(f"basic-pitch conversion failed for job {job_id}: {e}", exc_info=True)
        raise Exception(f"MIDI conversion failed: {e}")


async def upload_file(file_path: str, upload_url: str):
    """Uploads the generated MIDI file to the pre-signed output URL."""
    with open(file_path, 'rb') as f:
        content = f.read()

    headers = {'Content-Type': 'audio/midi'}

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.put(upload_url, content=content, headers=headers)
        response.raise_for_status()

    logger.info(f"Successfully uploaded file to {upload_url}")