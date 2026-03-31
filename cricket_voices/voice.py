import os
import time
import asyncio
import edge_tts
import threading
from queue import Queue

VOICE_FOLDER = "C:/cricket_voices/"
VOICE = "bn-BD-NabanitaNeural"

# ---------------------------------------
# VOICE SYSTEM
# ---------------------------------------

voice_queue = Queue()

def voice_worker():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    while True:
        event, text, final, temp = voice_queue.get()
        try:
            # Generate temp file
            loop.run_until_complete(generate_voice(text, temp))
            
            # Ensure the temp file is fully written
            time.sleep(0.1)
            
            # 🔁 Retry file operations
            for i in range(10):  # More retries
                try:
                    # Remove read-only attribute if file exists
                    if os.path.exists(final):
                        try:
                            os.chmod(final, 0o777)
                        except:
                            pass
                        os.remove(final)
                    
                    # Rename temp to final
                    os.rename(temp, final)
                    print(f"✅ Successfully created: {final}")
                    break
                    
                except PermissionError:
                    print(f"⚠️ Permission denied, retrying... ({i+1}/10)")
                    time.sleep(0.5)
                except Exception as e:
                    print(f"❌ File operation error: {e}")
                    break
                    
        except Exception as e:
            print(f"🔊 Voice generation error: {e}")
        finally:
            voice_queue.task_done()

# Start the voice worker thread
worker_thread = threading.Thread(target=voice_worker, daemon=True)
worker_thread.start()

async def generate_voice(text, path):
    try:
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(path)
        print(f"🎵 Generated audio: {path}")
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        raise

def speak(event, text):
    print(f"🎙 Queued: {text}")
    os.makedirs(VOICE_FOLDER, exist_ok=True)
    final = os.path.join(VOICE_FOLDER, f"{event}.mp3")
    temp = final + ".tmp"
    
    # Make sure temp file doesn't exist
    if os.path.exists(temp):
        try:
            os.remove(temp)
        except:
            pass
    
    voice_queue.put((event, text, final, temp))
    print(f"📝 {event}: {text[:50]}...")

# ---------------------------------------
"""def main():
    # Test multiple events
    events = [
        ("OVER_COMPLETE", "ওভার শেষ হয়েছে, দলের সংগ্রহ ভালোভাবে এগুচ্ছে।"),
        ("BOUNDARY", "চমৎকার! চার রান! দারুণ শট!"),
        ("WICKET", "উইকেট! দারুণ বোলিং!")
    ]
    
    for event, text in events:
        speak(event, text)
        time.sleep(0.5)  # Small delay between queueing
    
    # Wait for all voices to be generated
    time.sleep(5)
    print("✅ All voices generated!")

if __name__ == "__main__":
    main()"""
