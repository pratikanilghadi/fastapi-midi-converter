from fastapi import HTTPException
from pydantic import HttpUrl, Dict, AnyHttpUrl
import httpx
import logging
import tempfile
from pathlib import Path
import librosa
import numpy as np
import os

from basic_pitch.inference import predict_and_save
from basic_pitch import ICASSP_2022_MODEL_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from model import AudioToMidiRequest

SUPPORTED_AUDIO_FORMATS = {'.wav', '.mp3', '.flac', '.m4a', '.ogg', '.aac'}


async def validate_audio_download_url(download_url: HttpUrl):
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.head(str(download_url))
            if response.status_code not in [200, 302]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Audio download URL not accessible: {response.status_code}"
                )
            content_type = response.headers.get('content-type','').lower()
            if content_type and not any(fmt in content_type for fmt in ['audio', 'mpeg', 'wav', 'flac']):
                logger.warning(f"Unexpected content type: {content_type}")
        
        except httpx.RequestError as e:
            raise HTTPException(status_code=400, detail=f"Audio download URL error : {str(e)}")

async def validate_midi_upload_url(upload_url: HttpUrl):
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test upload URL accessibility
            response = await client.options(str(upload_url))
            logger.info(f"MIDI upload URL test response: {response.status_code}")
        except httpx.RequestError as e:
            logger.warning(f"MIDI upload URL test warning: {str(e)}")

async def process_audio_to_midi(processing_id: str, request: AudioToMidiRequest):
    temp_dir = None
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Step 1: Download audio file
        audio_file_path = await download_audio_file(
            str(request.audio_download_url),
            temp_dir,
            request.audio_file_name
        )
        
        # Step 2: Analyze audio file
        audio_info = await analyse_audio_file(audio_file_path)
        
        # Step 3: Convert to MIDI using basic-pitch
        midi_file_path = await convert_audio_to_midi_basic_pitch(
            audio_file_path, 
            temp_dir, 
            request,
            processing_id
        )
        
        # Step 4: Analyze MIDI file
        midi_info = await analyze_midi_file(midi_file_path)
        
        # Step 5: Upload MIDI file
        await upload_midi_file(midi_file_path, str(request.midi_upload_url))
        
        # Completion
        logger.info(f"Processing {processing_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Processing {processing_id} failed: {str(e)}")
        
    finally:
        # Cleanup temporary files
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory: {str(e)}")

async def download_audio_file(download_url: str, temp_dir: str, file_name: str = None):
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.get(download_url)
        response.raise_for_status()

        if file_name:
            file_extension = Path(file_name).suffix.lower()
        else:
            file_extension = '.wav'
        
        if file_name not in SUPPORTED_AUDIO_FORMATS:
            file_extension = '.wav'

        audio_file_path = os.path.join(temp_dir, f"input_audio{file_extension}")

        with open(audio_file_path, 'wb') as f:
            f.write(response.content)

        logger.info(f"Downloaded audio file: {len(response.content)} bytes")
        return audio_file_path
    
async def analyse_audio_file(audio_file_path: str) -> dict:
    try:
        y, sr = librosa.load(audio_file_path)

        duration = len(y) / sr

        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]

        return {
            'duration_seconds': float(duration),
            'sample_rate': int(sr),
            'tempo_bpm': float(tempo),
            'file_size_mb': os.path.getsize(audio_file_path) / (1024*1024),
            'spectral_centroid_mean': float(np.mean(spectral_centroids)),
            'spectral_centroid_mean': float(np.mean(spectral_rolloff))
        } 
    
    except Exception as e:
        logger.warning(f"Audio analysis failed: {str(e)}")
        return {
            "duration_seconds": 0,
            "analysis_error": str(e)
        }
    
async def convert_audio_to_midi_basic_pitch(
        audio_file_path: str,
        temp_dir: str,
        request: AudioToMidiRequest,
        processing_id: str
) -> str:
    try:
        output_dir = os.path.join(temp_dir, "midi_output")
        os.makedirs(output_dir, exist_ok=True)

        predict_and_save(
            audio_path_list=[audio_file_path],
            output_directory=output_dir,
            save_midi=True,
            sonify_midi=False,  # Don't create audio files
            save_model_outputs=False,  # Don't save raw model outputs
            save_notes=False,  # Don't save note events
            model_path=ICASSP_2022_MODEL_PATH,
        )

        midi_files = list(Path(output_dir).glob("*.mid"))
        if not midi_files:
            raise Exception("No MIDI file was generated by basic_pitch")
        
        midi_file_path = str(midi_files[0])

        logger.info(f"MIDI file generated: {midi_file_path}")
        return midi_file_path

    except Exception as e:
        logger.error(f"basic-pitch conversion failed: {str(e)}")
        raise Exception(f"MIDI conversion failed: {str(e)}")

async def analyze_midi_file(midi_file_path: str) -> dict:
    try:
        import pretty_midi
        
        midi_data = pretty_midi.PrettyMIDI(midi_file_path)
        
        return {
            "duration_seconds": float(midi_data.get_end_time()),
            "num_instruments": len(midi_data.instruments),
            "num_notes": sum(len(instrument.notes) for instrument in midi_data.instruments),
            "tempo_changes": len(midi_data.tempo_changes),
            "file_size_kb": os.path.getsize(midi_file_path) / 1024,
            "estimated_tempo": midi_data.estimate_tempo() if midi_data.instruments else None
        }
        
    except Exception as e:
        logger.warning(f"MIDI analysis failed: {str(e)}")
        return {
            "file_size_kb": os.path.getsize(midi_file_path) / 1024,
            "analysis_error": str(e)
        }
    
async def upload_midi_file(midi_file_path: str, upload_url: str):
    """
    Upload MIDI file to signed URL
    """
    async with httpx.AsyncClient(timeout=300.0) as client:
        with open(midi_file_path, 'rb') as f:
            midi_content = f.read()
            
        headers = {
            'Content-Type': 'audio/midi',
            'Content-Length': str(len(midi_content))
        }
        
        response = await client.put(upload_url, content=midi_content, headers=headers)
        response.raise_for_status()
        
        logger.info(f"MIDI file uploaded successfully: {len(midi_content)} bytes")