from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import httpx

from model import ProcessingRequest, SuccessResponse, ErrorResponse
from worker import run_audio_to_midi_job

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Audio to Midi Converter",
    description="A production-ready service to convert audio files to MIDI.",
    version="1.0.0"
)

# === Exception Handlers for Consistent Error Responses ===

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles Pydantic model validation errors."""
    error_messages = '; '.join([f"{err['loc'][-1]}: {err['msg']}" for err in exc.errors()])
    logger.warning(f"Validation error: {error_messages}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            message=f"Invalid request body: {error_messages}",
            error="VALIDATION_ERROR"
        ).model_dump(by_alias=True)
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handles custom thrown HTTPErrors."""
    logger.error(f"HTTP exception: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            message=exc.detail,
            error="INVALID_INPUT"
        ).model_dump(by_alias=True)
    )

# === API Endpoint ===

@app.post(
    "/process",
    response_model=SuccessResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    tags=["Processing"]
)
async def create_processing_job(
    request: ProcessingRequest,
    background_tasks: BackgroundTasks
):
    """
    Accepts an audio-to-MIDI conversion job, validates input,
    and queues it for background processing.
    """
    logger.info(f"Received job request: {request.job_id}")

    # Quick validation of URLs before accepting the job
    await validate_url_is_accessible(str(request.input_file_url))
    
    # Add the heavy processing to the background
    background_tasks.add_task(run_audio_to_midi_job, request)

    return SuccessResponse(
        message="Processing accepted and initiated successfully.",
        job_id=request.job_id
    )

async def validate_url_is_accessible(url: str):
    """
    Performs a HEAD request to ensure the URL is accessible before starting
    the background task. This provides faster user feedback.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.head(url)
            # Raise an error for non-successful status codes (e.g., 403, 404, 500)
            response.raise_for_status()
    except httpx.RequestError as e:
        logger.warning(f"Input URL validation failed for {url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input file URL: Could not connect or timed out."
        )
    except httpx.HTTPStatusError as e:
        logger.warning(f"Input URL validation failed for {url}: Status {e.response.status_code}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input file URL: Resource returned status {e.response.status_code}."
        )
    
@app.get("/health")
def get_server_health():
    return {"Status":"Server is Running"}