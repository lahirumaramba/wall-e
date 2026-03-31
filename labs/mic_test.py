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
TEST_FILE = "wall_e_test.wav"

def test_playback():
    print(f"--- 1. Testing Speaker ({SPEAKER_HW}) ---")
    print("Playing a test beep...")
    # Using a built-in ALSA test sound
    subprocess.run(["aplay", "-D", SPEAKER_HW, "/usr/share/sounds/alsa/Front_Center.wav"])

def test_record():
    print(f"\n--- 2. Testing USB Mic ({MIC_HW}) ---")
    print("RECORDING START: Speak for 5 seconds...")
    # -f S16_LE (16-bit), -r 16000 (16kHz standard for Gemini)
    cmd = [
        "arecord", "-D", MIC_HW, 
        "-d", "5", "-f", "S16_LE", "-r", "16000", 
        TEST_FILE
    ]
    subprocess.run(cmd)
    print("RECORDING END.")

def test_loopback():
    if os.path.exists(TEST_FILE):
        print(f"\n--- 3. Loopback Test ---")
        print("Playing back your voice through the Rocky amp...")
        subprocess.run(["aplay", "-D", SPEAKER_HW, TEST_FILE])
    else:
        print("Error: The audio file was never created. Check Mic connection.")

if __name__ == "__main__":
    try:
        test_playback()
        time.sleep(1)
        test_record()
        time.sleep(1)
        test_loopback()
        print("\nHardware test complete!")
    except KeyboardInterrupt:
        print("\nTest cancelled.")