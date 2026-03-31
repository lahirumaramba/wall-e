# MIT License
# Copyright (c) 2026 Lahiru Maramba
# See the LICENSE file for details.

import os
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import time
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

# Load environment variables from .env file
load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_ID = os.getenv("MODEL_ID", "gemini-3.1-flash-image-preview")
DEVICE_INDEX = os.getenv("DEVICE_INDEX")  # Optional: Index from `uv run python -m sounddevice`
FS = 44100  # Sample rate
RECORD_SECONDS = 5
AUDIO_FILENAME = "labs/brain_mac_input.wav"
IMAGES_DIR = "images"

# Ensure images directory exists
os.makedirs(IMAGES_DIR, exist_ok=True)

if DEVICE_INDEX is not None:
    DEVICE_INDEX = int(DEVICE_INDEX)

def record_audio():
    """Records audio using sounddevice (Mac compatible)."""
    print(f"[*] Recording for {RECORD_SECONDS} seconds...")
    if DEVICE_INDEX is not None:
        print(f"[*] Using device index: {DEVICE_INDEX}")
    
    try:
        recording = sd.rec(
            int(RECORD_SECONDS * FS), 
            samplerate=FS, 
            channels=1, 
            dtype='int16',
            device=DEVICE_INDEX
        )
        sd.wait()  # Wait until recording is finished
        
        # Check for silence
        if np.abs(recording).max() == 0:
            print("[!] Warning: Recording is completely silent. Check your DEVICE_INDEX or mic permissions.")
            print("[*] Tip: Run `uv run python -m sounddevice` to see available devices and update your .env")
        
        wav.write(AUDIO_FILENAME, FS, recording)  # Save as WAV file
        print("[*] Recording complete.")
        return True
    except Exception as e:
        print(f"[!] Recording failed: {e}")
        return False

def process_with_gemini():
    """Sends recorded audio to Gemini API and generates an image in a single step."""
    if not GEMINI_API_KEY:
        print("[!] Error: GEMINI_API_KEY not found in .env file.")
        print("[!] Please add your Gemini API Key to the .env file.")
        return

    client = genai.Client(api_key=GEMINI_API_KEY)

    print(f"[*] Sending audio to Gemini ({MODEL_ID})...")
    try:
        with open(AUDIO_FILENAME, "rb") as f:
            audio_bytes = f.read()

        # Build the prompt for multimodal output
        prompt = "Listen to this audio. It contains a description of an image. Generate that image in 3D chibi-style miniature concept style."
        
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[
                types.Part.from_bytes(
                    data=audio_bytes,
                    mime_type="audio/wav"
                ),
                prompt
            ],
            config=types.GenerateContentConfig(
                image_config=types.ImageConfig(
                    aspect_ratio="16:9"
                )
            )
        )
        
        # Process response parts
        image_saved = False
        for part in response.parts:
            if part.text:
                print(f"\n[Gemini]: {part.text}")
            
            if part.inline_data:
                # Use PIL to save the image
                img = part.as_image()
                
                # Create datestamped filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(IMAGES_DIR, f"wall_e_art_{timestamp}.png")
                
                img.save(filename)
                print(f"\n[✨] Wall-E generated art and saved it to: {filename}")
                image_saved = True
        
        if not image_saved:
            print("[!] Gemini did not return an image. Check if your prompt was clear or if the model supports it.")
            
    except Exception as e:
        print(f"[!] Gemini API error: {e}")

def main():
    if not os.path.exists(".env"):
        print("[!] .env file missing. Creating one from .env.example...")
        import shutil
        shutil.copy(".env.example", ".env")
        print("[!] Please update the .env file with your GEMINI_API_KEY and run again.")
        return

    if record_audio():
        process_with_gemini()

if __name__ == "__main__":
    main()
