# MIT License
# Copyright (c) 2026 Lahiru Maramba
# See the LICENSE file for details.

import os
import signal
import subprocess
import time
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

try:
    from inky.auto import auto
    INKY_AVAILABLE = True
except ImportError:
    INKY_AVAILABLE = False

try:
    import gpiod
    import gpiodevice
    from gpiod.line import Bias, Direction, Edge
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False


# Load environment variables from .env file
load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MIC_HW = os.getenv("MIC_HW", "plughw:CARD=Device,DEV=0")  # USB PnP Sound Device (from mic_test.py)
SPEAKER_HW = os.getenv("SPEAKER_HW", "plughw:CARD=sndrpigooglevoi,DEV=0")
RECORD_SECONDS = 5
AUDIO_FILENAME = "brain_input.wav"
MODEL_ID = os.getenv("MODEL_ID", "gemini-3.1-flash-image-preview")
IMAGES_DIR = "images"
SOUNDS_DIR = "sounds"

# Inky Impression Buttons (BCM GPIO numbers)
SW_A = 5

# Ensure images directory exists
os.makedirs(IMAGES_DIR, exist_ok=True)

def play_sound(sound_name, loop=False, background=False):
    """Plays a WAV file from the sounds directory."""
    filename = os.path.join(SOUNDS_DIR, sound_name)
    if not os.path.exists(filename):
        print(f"[!] Warning: Sound file {filename} not found.")
        return None

    # Base command for aplay
    cmd = ["aplay", "-D", SPEAKER_HW, filename]
    
    # If looping, we use a shell loop to restart aplay continuously
    if loop:
        cmd = ["sh", "-c", f"while true; do aplay -D {SPEAKER_HW} {filename}; done"]

    try:
        if loop or background:
            # Run in background with a new process group and return the process object
            return subprocess.Popen(
                cmd, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid
            )
        else:
            # Run and wait for completion
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        # Don't fail the whole script if sound fails (e.g. on Mac without aplay)
        pass
    return None


def display_on_inky(image_path):
    """Displays the generated image on the Inky Impression e-ink display."""
    if not INKY_AVAILABLE:
        return

    try:
        # ask_user=False for non-interactive environments
        inky_display = auto(ask_user=False)
    except Exception as e:
        # Only print if we're likely on a Pi but display is missing
        if os.path.exists("/sys/class/gpio"):
            print(f"[!] Inky Impression not found: {e}")
        return

    print(f"[*] Drawing image on Inky Impression ({inky_display.resolution[0]}x{inky_display.resolution[1]})...")
    try:
        img = Image.open(image_path)
        # Resize to fit the display
        resized_img = img.resize(inky_display.resolution)
        
        saturation = float(os.getenv("INKY_SATURATION", "0.5"))
        
        try:
            inky_display.set_image(resized_img, saturation=saturation)
        except TypeError:
            inky_display.set_image(resized_img)
            
        # Play the celebratory sound right as the hardware starts refreshing
        play_sound("tada.wav", background=True)
        inky_display.show()
        print("[✨] Image displayed on e-ink.")
        play_sound("success.wav")
    except Exception as e:
        print(f"[!] Failed to display image on Inky: {e}")
        play_sound("fail.wav")



def record_audio():
    """Records audio using arecord (Pi compatible)."""
    print(f"[*] Recording for {RECORD_SECONDS} seconds...")
    cmd = [
        "arecord", "-D", MIC_HW,
        "-d", str(RECORD_SECONDS),
        "-f", "S16_LE",
        "-r", "16000",
        AUDIO_FILENAME
    ]
    try:
        subprocess.run(cmd, check=True)
        print("[*] Recording complete.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Recording failed: {e}")
        play_sound("fail.wav")
        return False


def process_with_gemini():
    """Sends recorded audio to Gemini API and generates an image in a single step."""
    if not GEMINI_API_KEY:
        print("[!] Error: GEMINI_API_KEY not found in .env file.")
        return

    client = genai.Client(api_key=GEMINI_API_KEY)

    print(f"[*] Sending audio to Gemini ({MODEL_ID})...")
    try:
        with open(AUDIO_FILENAME, "rb") as f:
            audio_bytes = f.read()

        # Build the prompt for multimodal output
        prompt = "Listen to this audio. It contains a description of an image. Generate that image in 3D chibi-style miniature concept style."
        
        # Start processing sound loop
        processing_proc = play_sound("processing.wav", loop=True)
        
        try:
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
        finally:
            if processing_proc:
                try:
                    # Kill the entire process group (shell + aplay)
                    os.killpg(os.getpgid(processing_proc.pid), signal.SIGTERM)
                    processing_proc.wait(timeout=1)
                except Exception:
                    pass
                
                # Small delay to ensure audio device is released for the next sound
                time.sleep(0.2)

        
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
                
                # Update Inky display if available
                display_on_inky(filename)


        
        if not image_saved:
            print("[!] Gemini did not return an image. Check if your prompt was clear or if the model supports it.")
            
    except Exception as e:
        print(f"[!] Gemini API error: {e}")
        play_sound("fail.wav")


def trigger_brain():
    """Trigger the recording and Gemini processing flow."""
    play_sound("activate.wav", background=True)
    print("\n[!] Button A pressed! Activating Wall-E...")
    if record_audio():
        process_with_gemini()
    print("\n[*] Wall-E is ready again. Press Button A to start.")


def main():
    if not os.path.exists(".env"):
        print("[!] .env file missing. Please create one based on .env.example")
        return

    print("[*] Wall-E Brain is starting...")
    
    if GPIO_AVAILABLE and INKY_AVAILABLE:
        print("[*] Running in event-driven mode (waiting for Button A).")
        try:
            chip = gpiodevice.find_chip_by_platform()
            SW_A_OFFSET = chip.line_offset_from_id(SW_A)
            
            # Setup for Button A: Input, Pull-up, Falling edge detection
            INPUT_SETTINGS = gpiod.LineSettings(
                direction=Direction.INPUT, 
                bias=Bias.PULL_UP, 
                edge_detection=Edge.FALLING
            )
            
            line_config = {SW_A_OFFSET: INPUT_SETTINGS}
            request = chip.request_lines(consumer="wall-e", config=line_config)
            
            print("[*] Wall-E is ready. Press Button A to start.")
            play_sound("activate.wav")
            
            while True:
                # read_edge_events() blocks until an event occurs
                for event in request.read_edge_events():
                    if event.line_offset == SW_A_OFFSET:
                        trigger_brain()
        except Exception as e:
            print(f"[!] GPIO/Button error: {e}")
            print("[*] Falling back to direct execution...")
            if record_audio():
                process_with_gemini()
    else:
        print("[*] GPIO or Inky not available. Running direct execution...")
        if record_audio():
            process_with_gemini()

if __name__ == "__main__":
    main()
