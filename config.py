# config.py

import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Fetch the backend URL for status callbacks, with a default for local development
POLYGEN_BACKEND_URL = os.getenv("POLYGEN_BACKEND_URL", "http://localhost:3000")

# Define supported audio formats
SUPPORTED_AUDIO_FORMATS = {'.wav', '.mp3', '.flac', '.m4a', '.ogg', '.aac'}