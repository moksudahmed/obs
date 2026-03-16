from playwright.sync_api import sync_playwright
import re
import json
import time
import random
import asyncio
import threading
import edge_tts
import os

# ----------------------------------------------------
# CONFIG
# ----------------------------------------------------

CREX_URL = "https://crex.com/scoreboard/10XY/2FB/3rd-ODI/HP/PM/brn-vs-mas-3rd-odi-bahrain-tour-of-malaysia-2026/live"

REFRESH_INTERVAL = 2

VOICE = "bn-BD-NabanitaNeural"

VOICE_FILE = "C:/cricket_voices/voice.wav"

JSON_FILE = "C:/cricket_voices/score.json"


# ----------------------------------------------------
# COMMENTARY PACK
# ----------------------------------------------------

COMMENTARY = {

    "DOT": [
        "ডট বল",
        "দারুণ বল, কোনো রান নেই",
        "ব্যাটসম্যান ডিফেন্স করেছেন",
        "চমৎকার লাইন ও লেংথ",
        "বোলারের দারুণ বল"
    ],

    "SINGLE": [
        "এক রান নেওয়া হয়েছে",
        "সহজ সিঙ্গেল",
        "স্ট্রাইক রোটেট করলেন ব্যাটসম্যান"
    ],

    "DOUBLE": [
        "দুই রান সম্পন্ন",
        "দারুণ রানিং বিটুইন দ্য উইকেট"
    ],

    "TRIPLE": [
        "তিন রান নেওয়া হয়েছে",
        "দারুণ দৌড়ে তিন রান"
    ],

    "FOUR": [
        "চার! অসাধারণ শট",
        "গ্যাপ খুঁজে পেল ব্যাটসম্যান",
        "চমৎকার বাউন্ডারি",
        "দারুণ টাইমিং"
    ],

    "SIX": [
        "ছক্কা! বল উড়ে গেল গ্যালারিতে",
        "বিশাল ছক্কা",
        "অসাধারণ পাওয়ার হিট"
    ],

    "WICKET": [
        "আউট! বড় উইকেট",
        "ব্যাটসম্যান ফিরে যাচ্ছেন",
        "দারুণ ব্রেকথ্রু"
    ],

    "OVER": [
        "ওভার শেষ",
        "একটি ওভার সম্পন্ন হয়েছে"
    ]
}

# ----------------------------------------------------
# GLOBAL STATE
# ----------------------------------------------------

last_runs = None
last_wickets = None
last_over = None
last_event = "NONE"


# ----------------------------------------------------
# EDGE TTS SYSTEM
# ----------------------------------------------------

async def generate_voice(text):

    communicate = edge_tts.Communicate(text, VOICE)

    await communicate.save(VOICE_FILE)


def speak(text):

    def run():
        asyncio.run(generate_voice(text))

    t = threading.Thread(target=run)
    t.start()


# ----------------------------------------------------
# COMMENTARY SELECT
# ----------------------------------------------------

def get_commentary(event):

    if event in COMMENTARY:

        return random.choice(COMMENTARY[event])

    return None


# ----------------------------------------------------
# SCORE PARSER
# ----------------------------------------------------

def parse_score(page_text):

    score_match = re.search(r'(\d+)\s*-\s*(\d+)', page_text)

    over_match = re.search(r'(\d+)\.(\d+)\s*Ov', page_text)

    if not score_match:
        return None

    runs = int(score_match.group(1))
    wickets = int(score_match.group(2))

    over = 0

    if over_match:

        over = int(over_match.group(1))

    return runs, wickets, over


# ----------------------------------------------------
# EVENT DETECTION
# ----------------------------------------------------

def detect_event(runs, wickets, over):

    global last_runs, last_wickets, last_over

    if last_runs is None:

        last_runs = runs
        last_wickets = wickets
        last_over = over

        return "NONE"

    run_diff = runs - last_runs

    event = "NONE"

    if wickets > last_wickets:

        event = "WICKET"

    elif over > last_over:

        event = "OVER"

    elif run_diff == 0:

        event = "DOT"

    elif run_diff == 1:

        event = "SINGLE"

    elif run_diff == 2:

        event = "DOUBLE"

    elif run_diff == 3:

        event = "TRIPLE"

    elif run_diff == 4:

        event = "FOUR"

    elif run_diff >= 6:

        event = "SIX"

    last_runs = runs
    last_wickets = wickets
    last_over = over

    return event


# ----------------------------------------------------
# WRITE JSON (FOR OBS OVERLAY)
# ----------------------------------------------------

def write_json(runs, wickets, over, event):

    data = {

        "runs": runs,
        "wickets": wickets,
        "over": over,
        "event": event

    }

    with open(JSON_FILE, "w", encoding="utf-8") as f:

        json.dump(data, f, indent=4)


# ----------------------------------------------------
# SPEAK EVENT
# ----------------------------------------------------

def speak_event(event):

    global last_event

    if event == last_event:
        return

    last_event = event

    line = get_commentary(event)

    if line:

        print("EVENT:", event, "|", line)

        speak(line)


# ----------------------------------------------------
# MAIN SYSTEM
# ----------------------------------------------------

def main():

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        print("Opening match page...")

        page.goto(CREX_URL)

        while True:

            try:

                page.reload()

                text = page.inner_text("body")

                score_data = parse_score(text)

                if not score_data:

                    time.sleep(REFRESH_INTERVAL)
                    continue

                runs, wickets, over = score_data

                event = detect_event(runs, wickets, over)

                write_json(runs, wickets, over, event)

                if event != "NONE":

                    speak_event(event)

            except Exception as e:

                print("Error:", e)

            time.sleep(REFRESH_INTERVAL)


# ----------------------------------------------------
# START
# ----------------------------------------------------

if __name__ == "__main__":
    main()