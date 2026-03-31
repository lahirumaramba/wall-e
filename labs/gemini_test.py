# MIT License
# Copyright (c) 2026 Lahiru Maramba
# See the LICENSE file for details.

import time
import subprocess
import os
import RPi.GPIO as GPIO
from inky.auto import auto
from PIL import Image
from google import genai
from google.genai import types

# --- Hardware Configuration ---
# Card names from your 'aplay -l' and 'arecord -l'
SPEAKER_HW = "plughw:CARD=sndrpigooglevoi,DEV=0"
MIC_HW = "plughw:CARD=Device,DEV=0"
BUTTON_PIN = 5 # Button A on Inky Impression

# --- Gemini Configuration ---
API_KEY = "YOUR_GEMINI_API_KEY"
client = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-2.0-flash" 

# --- Inky Setup ---
display = auto()

# --- Functions ---
def play_sound(action):
    """Plays status sounds through the Rocky amp."""
    sounds = {
        "start": "/usr/share/sounds/alsa/Front_Center.wav", # Replace with your own pings
        "thinking": "/usr/share/sounds/alsa/Side_Left.wav",
        "done": "/usr/share/sounds/alsa/Side_Right.wav"
    }
    subprocess.Popen(["aplay", "-D", SPEAKER_HW, sounds.get(action)])

def record_audio(filename="prompt.wav", duration=5):
    """Records your voice command."""
    print(f"[*] Recording for {duration} seconds...")
    subprocess.run([
        "arecord", "-D", MIC_HW, "-d", str(duration), 
        "-f", "S16_LE", "-r", "16000", filename
    ])

def generate_art(audio_file):
    """Sends audio to Gemini and gets back an image."""
    print("[*] Sending to Gemini...")
    
    # Upload the audio file to Gemini
    uploaded_audio = client.files.upload(file=audio_file)
    
    # Prompt Gemini to listen and create
    prompt = "Listen to this audio. It contains a description of an image. Generate that image."
    
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=[prompt, uploaded_audio],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"]
        )
    )
    
    # Extract and save the image
    for part in response.parts:
        if part.inline_data:
            img = part.as_image()
            img.save("generated_art.png")
            return "generated_art.png"
    return None

def display_on_inky(image_path):
    """Prepares and pushes the image to the e-ink screen."""
    print("[*] Refreshing Inky (this takes ~20s)...")
    img = Image.open(image_path)
    img = img.resize(display.resolution)
    display.set_image(img)
    display.show()

# --- Main Loop ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("Ready! Press Button A to describe your art.")

try:
    while True:
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:
            play_sound("start")
            record_audio("prompt.wav")
            
            play_sound("thinking")
            image_path = generate_art("prompt.wav")
            
            if image_path:
                play_sound("done")
                display_on_inky(image_path)
            
            print("Done! Waiting for next command...")
            time.sleep(2) # Prevent double-trigger
        time.sleep(0.1)

except KeyboardInterrupt:
    GPIO.cleanup()