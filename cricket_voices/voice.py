import asyncio
import edge_tts
import os
import time
import threading
from queue import Queue
import glob
import json
import sys

# ==============================
# OBS INTEGRATION FUNCTION
# ==============================

def update_obs_ready_file(event, filepath):
    """
    Update OBS ready.json file and trigger OBS to play the voice
    This function works with the OBS Lua script's async queue system
    """
    ready_file = os.path.join(VOICE_FOLDER, "ready.json")
    
    try:
        # Load existing ready data
        ready_data = {}
        if os.path.exists(ready_file):
            with open(ready_file, 'r', encoding='utf-8') as f:
                try:
                    ready_data = json.load(f)
                except json.JSONDecodeError:
                    ready_data = {}
        
        # Update with new file
        ready_data[event] = filepath
        
        # Write atomically (write to temp then rename)
        temp_file = ready_file + '.tmp'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(ready_data, f, indent=2, ensure_ascii=False)
        
        # Atomic replace
        os.replace(temp_file, ready_file)
        
        print(f"✅ OBS ready: {event} -> {os.path.basename(filepath)}")
        
        # Small delay to ensure OBS reads the file
        time.sleep(0.05)
        
        return True
        
    except Exception as e:
        print(f"⚠️ Failed to update OBS ready file: {e}")
        return False

# ==============================
# CONFIG
# ==============================
VOICE_FOLDER = "C:/cricket_voices/"
VOICE = "bn-BD-NabanitaNeural"
READY_FILE = os.path.join(VOICE_FOLDER, "ready.json")

# Create folder with proper permissions
try:
    os.makedirs(VOICE_FOLDER, exist_ok=True)
    # Test write permission
    test_file = os.path.join(VOICE_FOLDER, "test_write.txt")
    with open(test_file, 'w') as f:
        f.write("test")
    os.remove(test_file)
    print(f"✅ Folder is writable: {VOICE_FOLDER}")
except Exception as e:
    print(f"❌ CRITICAL: Cannot write to {VOICE_FOLDER}: {e}")
    print("Please check folder permissions or run as administrator")
    sys.exit(1)

voice_queue = Queue()

# Anti-spam control
last_event = None
last_event_time = 0
EVENT_COOLDOWN = 2

# Track generation status
generating = {}
ready_files = {}

# ==============================
# UTILITIES
# ==============================

def delete_old_voice_file(event):
    """Delete the old voice file for the same event before generating new one"""
    try:
        pattern = os.path.join(VOICE_FOLDER, f"{event}_*.mp3")
        old_files = glob.glob(pattern)
        
        if old_files:
            for old_file in old_files:
                try:
                    os.remove(old_file)
                    print(f"🗑️ Deleted old file: {os.path.basename(old_file)}")
                except PermissionError:
                    print(f"⚠️ Could not delete (in use): {os.path.basename(old_file)}")
                except Exception as e:
                    print(f"⚠️ Error deleting {os.path.basename(old_file)}: {e}")
            return len(old_files)
        return 0
    except Exception as e:
        print(f"⚠️ Error scanning for old files: {e}")
        return 0

def get_timestamp_filename(event):
    """Generate timestamp-based filename"""
    timestamp = int(time.time() * 1000)
    return os.path.join(VOICE_FOLDER, f"{event}_{timestamp}.mp3")

def cleanup_old_files():
    """Remove old files keeping only latest 1 per event"""
    try:
        for event in ["WIDE", "SIX", "FOUR", "WICKET", "SINGLE", "DOUBLE", "DOT", 
                      "NO_BALL", "OVER", "WELCOME", "LAST_OVER", "TRIPLE", "TOSS"]:
            files = glob.glob(os.path.join(VOICE_FOLDER, f"{event}_*.mp3"))
            files.sort(key=os.path.getmtime, reverse=True)
            for old_file in files[1:]:
                try:
                    os.remove(old_file)
                    print(f"🧹 Cleanup removed: {os.path.basename(old_file)}")
                except:
                    pass
    except Exception as e:
        print(f"Cleanup error: {e}")

# ==============================
# TTS GENERATION (FIXED - Better error handling)
# ==============================

async def test_edge_tts():
    """Test if edge_tts is working properly"""
    try:
        test_file = os.path.join(VOICE_FOLDER, "test_connection.mp3")
        communicate = edge_tts.Communicate("পরীক্ষা", VOICE)
        await communicate.save(test_file)
        
        if os.path.exists(test_file) and os.path.getsize(test_file) > 1000:
            os.remove(test_file)
            print("✅ Edge TTS connection successful")
            return True
        else:
            print("❌ Edge TTS test failed - file not created properly")
            return False
    except Exception as e:
        print(f"❌ Edge TTS connection failed: {e}")
        return False

async def generate_voice(text, filepath):
    """Generate voice directly to MP3 file with comprehensive error handling"""
    
    # Validate input
    if not text or not text.strip():
        print(f"  ❌ Empty text provided")
        return False
    
    print(f"  📝 Text to speak: '{text[:50]}...' (length: {len(text)})")
    
    for attempt in range(3):
        try:
            print(f"  🔄 Attempt {attempt + 1}/3: Generating {os.path.basename(filepath)}...")
            
            # Create the communicate object
            communicate = edge_tts.Communicate(text, VOICE)
            
            # Save the file with timeout
            await asyncio.wait_for(communicate.save(filepath), timeout=30.0)
            
            # Small delay to ensure file is written
            await asyncio.sleep(0.5)
            
            # Verify file was created and has content
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                print(f"  📊 File size: {file_size} bytes")
                
                if file_size > 2000:  # Increased threshold for Bengali voice
                    print(f"  ✅ Generated successfully: {os.path.basename(filepath)} ({file_size} bytes)")
                    return True
                elif file_size > 500:
                    print(f"  ⚠️ File smaller than expected: {file_size} bytes, but accepting")
                    return True
                else:
                    print(f"  ⚠️ File too small: {file_size} bytes, retrying...")
                    # Delete corrupted file
                    try:
                        os.remove(filepath)
                    except:
                        pass
            else:
                print(f"  ⚠️ File not created on attempt {attempt + 1}")
                
        except asyncio.TimeoutError:
            print(f"  ⏰ Timeout on attempt {attempt + 1} (30 seconds)")
        except ConnectionError as e:
            print(f"  🌐 Network error on attempt {attempt + 1}: {e}")
        except Exception as e:
            print(f"  ❌ Error on attempt {attempt + 1}: {type(e).__name__}: {e}")
            
        # Wait before retry with exponential backoff
        if attempt < 2:
            wait_time = (attempt + 1) * 1.5
            print(f"  ⏳ Waiting {wait_time}s before retry...")
            await asyncio.sleep(wait_time)
    
    print(f"  ❌ Failed to generate after 3 attempts")
    return False

# ==============================
# WORKER THREAD (FIXED - Better error handling)
# ==============================

def voice_worker():
    """Background worker for voice generation with better error handling"""
    # Create new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Test edge_tts connection first
    print("\n🔍 Testing Edge TTS connection...")
    try:
        test_result = loop.run_until_complete(test_edge_tts())
        if not test_result:
            print("⚠️ Warning: Edge TTS test failed, but will continue trying")
    except Exception as e:
        print(f"⚠️ Test error: {e}")
    
    while True:
        try:
            event, text = voice_queue.get()
            
            print(f"\n{'='*50}")
            print(f"🎙 Processing: {event}")
            print(f"📝 Text: {text}")
            
            # Delete old voice file for this event
            deleted_count = delete_old_voice_file(event)
            if deleted_count > 0:
                print(f"📁 Deleted {deleted_count} old file(s)")
            
            # Mark as generating
            generating[event] = True
            
            # Generate new filename with timestamp
            filename = get_timestamp_filename(event)
            print(f"🔄 Target file: {os.path.basename(filename)}")
            
            # Generate directly to final file
            success = loop.run_until_complete(generate_voice(text, filename))
            
            if success and os.path.exists(filename):
                file_size = os.path.getsize(filename)
                if file_size > 500:  # Accept files > 500 bytes
                    print(f"✅ Successfully created: {os.path.basename(filename)} ({file_size} bytes)")
                    
                    from datetime import datetime
                    print(f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}")
                    
                    # Mark as ready for OBS
                    update_obs_ready_file(event, filename)
                    
                    # Also store in local cache
                    ready_files[event] = filename
                    
                    # Small delay before cleanup
                    time.sleep(0.2)
                    cleanup_old_files()
                else:
                    print(f"❌ File validation failed: file too small ({file_size} bytes)")
                    # Try to delete the corrupted file
                    try:
                        os.remove(filename)
                    except:
                        pass
            else:
                print(f"❌ Generation failed for: {event}")
                # Try to get existing file as fallback
                existing_files = glob.glob(os.path.join(VOICE_FOLDER, f"{event}_*.mp3"))
                if existing_files:
                    latest = max(existing_files, key=os.path.getmtime)
                    print(f"🔄 Using existing file as fallback: {os.path.basename(latest)}")
                    update_obs_ready_file(event, latest)
                
        except Exception as e:
            print(f"❌ Critical error in worker: {e}")
            import traceback
            traceback.print_exc()
        finally:
            generating[event] = False
            voice_queue.task_done()
            print(f"{'='*50}\n")

# ==============================
# PUBLIC API
# ==============================

def speak(event, text):
    """Queue voice for generation"""
    global last_event, last_event_time
    
    if not event or not text:
        print(f"⚠️ Invalid speak call: event={event}, text={text}")
        return
    
    now = time.time()
    
    # Anti-spam
    if event == last_event and (now - last_event_time) < EVENT_COOLDOWN:
        print(f"⏩ Skipped duplicate: {event}")
        return
    
    last_event = event
    last_event_time = now
    
    voice_queue.put((event, text))
    print(f"📝 Queued: {event} (Queue size: {voice_queue.qsize()})")

def get_ready_file(event):
    """Get ready file if available (for OBS)"""
    if event in ready_files:
        filepath = ready_files[event]
        if os.path.exists(filepath):
            return filepath
    return None

def is_generating(event):
    """Check if event is currently being generated"""
    return generating.get(event, False)

def get_latest_file(event):
    """Get latest file by scanning folder"""
    files = glob.glob(os.path.join(VOICE_FOLDER, f"{event}_*.mp3"))
    if files:
        files.sort(key=os.path.getmtime, reverse=True)
        return files[0]
    return None

def list_voice_files():
    """List all voice files in folder (for debugging)"""
    files = glob.glob(os.path.join(VOICE_FOLDER, "*_*.mp3"))
    if files:
        print("\n📁 Current voice files:")
        for f in sorted(files):
            size = os.path.getsize(f)
            print(f"   {os.path.basename(f)} ({size} bytes)")
    else:
        print("\n📁 No voice files found")
    return files

def force_cleanup_all():
    """Force delete all voice files (use with caution)"""
    files = glob.glob(os.path.join(VOICE_FOLDER, "*_*.mp3"))
    for f in files:
        try:
            os.remove(f)
            print(f"🗑️ Deleted: {os.path.basename(f)}")
        except:
            pass
    if os.path.exists(READY_FILE):
        os.remove(READY_FILE)
    ready_files.clear()
    print("✅ All voice files cleaned up")

def test_single_voice(event, text):
    """Test a single voice generation synchronously"""
    print(f"\n🧪 Testing voice generation for: {event}")
    print(f"📝 Text: {text}")
    
    # Delete old files
    delete_old_voice_file(event)
    
    # Generate new file
    filename = get_timestamp_filename(event)
    print(f"🔄 Generating: {os.path.basename(filename)}")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    success = loop.run_until_complete(generate_voice(text, filename))
    loop.close()
    
    if success:
        print(f"✅ Test successful: {filename}")
        list_voice_files()
        return True
    else:
        print(f"❌ Test failed for: {event}")
        return False

# ==============================
# STARTUP
# ==============================

print("\n" + "="*60)
print("🎤 VOICE SYSTEM STARTING...")
print("="*60)

# Clear old ready file
if os.path.exists(READY_FILE):
    try:
        os.remove(READY_FILE)
        print("🧹 Cleared old ready.json")
    except Exception as e:
        print(f"⚠️ Could not clear ready.json: {e}")

# Initial cleanup of old files
print("🧹 Performing initial cleanup...")
cleanup_old_files()

# Start worker thread
worker_thread = threading.Thread(target=voice_worker, daemon=True)
worker_thread.start()

print("=" * 60)
print("🎤 VOICE SYSTEM READY - DEBUG VERSION")
print(f"📁 Folder: {VOICE_FOLDER}")
print(f"🗣️  Voice: {VOICE}")
print("🐛 Debug mode: ENABLED")
print("✅ OBS integration enabled")
print("=" * 60)

# List current files after cleanup
list_voice_files()

print("\n💡 Tip: Run test_single_voice('TEST', 'পরীক্ষা') to test generation")
print("=" * 60 + "\n")
