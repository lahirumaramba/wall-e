# MIT License
# Copyright (c) 2026 Lahiru Maramba
# See the LICENSE file for details.

import subprocess
import time
import os

# --- Hardware Configuration ---
# Card names from your 'aplay -l' and 'arecord -l'
SPEAKER_HW = "plughw:CARD=sndrpigooglevoi,DEV=0"
MIC_HW = "plughw:CARD=Device,DEV=0"
WAVE_OUTPUT_FILENAME = "audio_test_output.wav"
RECORD_SECONDS = 5

def record_audio():
    print(f"[*] Recording from {MIC_HW} for {RECORD_SECONDS} seconds...")
    # -f S16_LE (16-bit), -r 16000 (16kHz standard)
    # Using 16000Hz as it's often more stable for USB mics on Pi Zero
    cmd = [
        "arecord", "-D", MIC_HW, 
        "-d", str(RECORD_SECONDS), 
        "-f", "S16_LE", 
        "-r", "16000", 
        WAVE_OUTPUT_FILENAME
    ]
    try:
        subprocess.run(cmd, check=True)
        print("[*] Done recording.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Recording failed: {e}")
        return False

def play_audio():
    if not os.path.exists(WAVE_OUTPUT_FILENAME):
        print(f"[!] Error: {WAVE_OUTPUT_FILENAME} not found.")
        return

    print(f"[*] Playing back through {SPEAKER_HW}...")
    cmd = ["aplay", "-D", SPEAKER_HW, WAVE_OUTPUT_FILENAME]
    try:
        subprocess.run(cmd, check=True)
        print("[*] Done playing.")
    except subprocess.CalledProcessError as e:
        print(f"[!] Playback failed: {e}")

if __name__ == "__main__":
    if record_audio():
        time.sleep(1)  # small pause before playing
        play_audio()
