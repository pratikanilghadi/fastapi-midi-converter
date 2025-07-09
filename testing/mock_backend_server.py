import os
from flask import Flask, request, jsonify, send_from_directory
import json

# --- Configuration ---
HOST = 'localhost'
PORT = 3000
TEST_FILES_DIR = 'test-files'
UPLOAD_DIR = 'test-uploads'

# --- Flask App Setup ---
app = Flask(__name__)

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
    print(f"Created upload directory: {UPLOAD_DIR}")

# --- Helper Function ---
def pretty_print_json(data):
    """Prints JSON data with indentation for readability."""
    print(json.dumps(data, indent=2))

# --- API Endpoints to Mimic Your Main Application ---

@app.route('/api/users/jobs/<jobId>/callback', methods=['POST'])
def job_callback(jobId):
    """
    This is the endpoint your FastAPI service will call to post status updates.
    """
    print("\n" + "="*50)
    print(f"===> Received Callback for Job ID: {jobId}")
    print("="*50)
    
    if request.is_json:
        status_data = request.get_json()
        print("Status Update Payload:")
        pretty_print_json(status_data)
        
        if status_data.get("status") == "completed":
            print("\n---> JOB COMPLETED! <---")
        elif status_data.get("status") == "failed":
            print("\n---> !!! JOB FAILED !!! <---")

    else:
        print("Received non-JSON request body.")
        print(request.get_data())
        
    return jsonify({"status": "callback_received"}), 200

@app.route('/test-files/<filename>', methods=['GET'])
def download_test_file(filename):
    """
    This endpoint serves the sample audio file for your service to download.
    """
    print(f"\n[INFO] Serving download request for: {filename}")
    return send_from_directory(TEST_FILES_DIR, filename)

@app.route('/test-files/<filename>', methods=['PUT'])
def upload_processed_file(filename):
    """
    This endpoint simulates a pre-signed URL, accepting the final MIDI file upload.
    """
    upload_path = os.path.join(UPLOAD_DIR, filename)
    with open(upload_path, 'wb') as f:
        f.write(request.data)
    
    file_size = len(request.data)
    print("\n" + "*"*50)
    print(f"[SUCCESS] Received uploaded file '{filename}' ({file_size} bytes).")
    print(f"Saved to: {upload_path}")
    print("*"*50)
    return '', 200

# --- Main execution ---
if __name__ == '__main__':
    print(f"Mock Backend Server running at http://{HOST}:{PORT}")
    print("It will:")
    print(f"1. Serve files from the '{TEST_FILES_DIR}' directory.")
    print(f"2. Accept MIDI uploads to the '{UPLOAD_DIR}' directory.")
    print(f"3. Listen for job status callbacks at /api/users/jobs/<jobId>/callback")
    print("\nPress CTRL+C to stop.")
    app.run(host=HOST, port=PORT)