import asyncio
import edge_tts
import os
import time
import threading
from queue import Queue
import shutil
import tempfile

VOICE_FOLDER = "C:/cricket_voices/"
VOICE = "bn-BD-NabanitaNeural"

# Create voice folder if it doesn't exist
os.makedirs(VOICE_FOLDER, exist_ok=True)

voice_queue = Queue()
file_lock = threading.Lock()

def cleanup_temp_files():
    """Remove temporary files from previous runs"""
    try:
        count = 0
        for file in os.listdir(VOICE_FOLDER):
            if any(x in file for x in ['.tmp', '_temp_', '.backup']):
                try:
                    os.remove(os.path.join(VOICE_FOLDER, file))
                    count += 1
                except:
                    pass
        if count > 0:
            print(f"🧹 Removed {count} temp files")
    except Exception as e:
        print(f"⚠️ Cleanup error: {e}")

def wait_for_file_release(filepath, max_wait=3):
    """Wait for file to be released by other processes"""
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            # Try to open file in append mode
            with open(filepath, 'ab') as f:
                f.write(b'')
                return True
        except (IOError, PermissionError):
            time.sleep(0.2)
        except FileNotFoundError:
            return True
    return False

def safe_replace_file(temp_file, final_file, max_retries=10):
    """Safely replace file with retry mechanism"""
    for attempt in range(max_retries):
        try:
            # Check if final file exists
            if os.path.exists(final_file):
                # Wait for file to be released
                wait_for_file_release(final_file)
                
                # Try multiple ways to remove the file
                removed = False
                for remove_attempt in range(3):
                    try:
                        os.remove(final_file)
                        removed = True
                        time.sleep(0.1)
                        break
                    except PermissionError:
                        time.sleep(0.3)
                    except FileNotFoundError:
                        removed = True
                        break
                
                # If still exists, try to rename it
                if not removed and os.path.exists(final_file):
                    try:
                        backup_file = final_file + f".backup_{int(time.time())}"
                        os.rename(final_file, backup_file)
                        time.sleep(0.1)
                    except:
                        pass
            
            # Now try to rename temp to final
            os.rename(temp_file, final_file)
            print(f"✅ Voice file ready: {os.path.basename(final_file)}")
            return True
            
        except FileExistsError as e:
            # File already exists - try to remove and retry
            if attempt < max_retries - 1:
                try:
                    if os.path.exists(final_file):
                        os.remove(final_file)
                        time.sleep(0.2)
                except:
                    pass
                time.sleep(0.3)
            else:
                # Last attempt - try to overwrite by copying
                try:
                    shutil.copy2(temp_file, final_file)
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    print(f"✅ Voice copied (overwrite): {os.path.basename(final_file)}")
                    return True
                except Exception as copy_err:
                    print(f"❌ Failed to overwrite: {copy_err}")
                    
        except PermissionError:
            if attempt == max_retries - 1:
                # Last attempt - try copy method
                try:
                    shutil.copy2(temp_file, final_file)
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    print(f"✅ Voice copied (fallback): {os.path.basename(final_file)}")
                    return True
                except Exception as e:
                    print(f"❌ Failed to create voice file: {e}")
            else:
                time.sleep(0.5)
                
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"❌ Failed after {max_retries} attempts: {e}")
            else:
                time.sleep(0.3)
    
    return False

def voice_worker():
    """Background worker for voice generation"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    while True:
        event, text, final, temp = voice_queue.get()
        try:
            print(f"🎙 Generating voice for: {event}")
            
            # Generate temp file
            loop.run_until_complete(generate_voice(text, temp))
            
            # Verify temp file was created and has content
            if not os.path.exists(temp):
                print(f"❌ Temp file not created: {temp}")
                continue
            
            # Check file size
            file_size = os.path.getsize(temp)
            if file_size < 1000:  # Less than 1KB probably means error
                print(f"⚠️ Temp file too small ({file_size} bytes), might be invalid")
                continue
            
            # Wait a bit for file to be fully written
            time.sleep(0.3)
            
            # Safe replace
            if safe_replace_file(temp, final):
                print(f"🔊 Voice ready: {event}")
            else:
                print(f"❌ Failed to create voice file for {event}")
                # Clean up temp file if failed
                try:
                    if os.path.exists(temp):
                        os.remove(temp)
                except:
                    pass
                
        except Exception as e:
            print(f"❌ Voice Error for {event}: {e}")
        finally:
            voice_queue.task_done()

async def generate_voice(text, path):
    """Generate voice using edge-tts"""
    try:
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(path)
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        raise

def speak(event, text):
    """Queue voice for speaking"""
    try:
        # Clean event name for filename
        safe_event = event.replace(" ", "_").replace("/", "_").replace("\\", "_")
        final = os.path.join(VOICE_FOLDER, f"{safe_event}.mp3")
        
        # Use timestamp to ensure unique temp filename
        timestamp = int(time.time() * 1000)
        temp = os.path.join(VOICE_FOLDER, f"{safe_event}_temp_{timestamp}.mp3")
        
        voice_queue.put((event, text, final, temp))
        print(f"📝 Queued: {event}")
        
    except Exception as e:
        print(f"❌ Speak error: {e}")

def pre_generate_voices():
    """Pre-generate common commentary files to avoid runtime issues"""
    common_events = {
        "DOT": "ডট বল।",
        "SINGLE": "এক রান।",
        "DOUBLE": "দুই রান।",
        "FOUR": "চার রান।",
        "SIX": "ছয় রান।",
        "WIDE": "ওয়াইড বল।",
        "NO_BALL": "নো বল।",
        "OVER_COMPLETE": "ওভার শেষ।",
        "WELCOME": "স্বাগতম।",
        "WICKET": "উইকেট পতন।"
    }
    
    for event, short_text in common_events.items():
        final = os.path.join(VOICE_FOLDER, f"{event}.mp3")
        if not os.path.exists(final):
            print(f"🔄 Pre-generating {event}...")
            speak(event, short_text)
    
    # Wait for pre-generation to complete
    time.sleep(5)
    print("✅ Pre-generation complete")

# Function to directly write file (bypassing queue for testing)
def speak_direct(event, text):
    """Directly generate and save voice file (bypasses queue)"""
    try:
        safe_event = event.replace(" ", "_").replace("/", "_").replace("\\", "_")
        final = os.path.join(VOICE_FOLDER, f"{safe_event}.mp3")
        temp = os.path.join(VOICE_FOLDER, f"{safe_event}_temp_{int(time.time() * 1000)}.mp3")
        
        # Run async generation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(generate_voice(text, temp))
        loop.close()
        
        if os.path.exists(temp):
            time.sleep(0.2)
            if safe_replace_file(temp, final):
                print(f"✅ Direct voice saved: {event}")
                return True
        return False
    except Exception as e:
        print(f"❌ Direct voice error: {e}")
        return False

# Start worker thread
worker_thread = threading.Thread(target=voice_worker, daemon=True)
worker_thread.start()

# Run cleanup on import
cleanup_temp_files()

# Optional: Pre-generate common voices
# Uncomment the line below to pre-generate voices at startup
# pre_generate_voices()
