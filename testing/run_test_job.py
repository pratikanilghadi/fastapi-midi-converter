import requests
import uuid
import json

# --- Configuration ---
# URL of your running FastAPI service
FASTAPI_SERVICE_URL = "http://localhost:8000/process"

# Base URL of the mock backend server we are running
MOCK_BACKEND_URL = "http://localhost:3000"

# --- Main Test Function ---
def run_test():
    """
    Creates and sends a new audio-to-MIDI job request.
    """
    job_id = str(uuid.uuid4())
    audio_file_name = "sample_audio.mp3"
    output_file_name = f"output_{job_id}.mid"
    
    # This payload mimics the request your application expects.
    # The URLs point to our mock_backend_server.
    job_payload = {
      "jobId": job_id,
      "userId": "test_user_001",
      "inputFileUrl": f"{MOCK_BACKEND_URL}/test-files/{audio_file_name}",
      "outputFileUrl": f"{MOCK_BACKEND_URL}/test-files/{output_file_name}",
      "processingType": "AUDIO2MIDI",
      "metadata": {
        "fileType": "AUDIO",
        "fileName": audio_file_name,
        "originalFileId": "test_audio_id_123",
        "fileSize": 123456 # This can be an arbitrary number for the test
      }
    }

    print("="*50)
    print(f"Submitting Job with ID: {job_id}")
    print("Request Payload:")
    print(json.dumps(job_payload, indent=2))
    print("="*50)

    try:
        response = requests.post(FASTAPI_SERVICE_URL, json=job_payload)
        response.raise_for_status()

        print("\n--- FastAPI Service Response ---")
        print(f"Status Code: {response.status_code}")
        print("Response Body:")
        print(json.dumps(response.json(), indent=2))
        print("\nJob successfully submitted! Watch the other terminals for progress.")

    except requests.exceptions.RequestException as e:
        print("\n--- ERROR ---")
        print(f"Failed to connect to the FastAPI service at {FASTAPI_SERVICE_URL}")
        print("Please ensure the uvicorn server is running.")
        print(f"Error details: {e}")

if __name__ == '__main__':
    run_test()