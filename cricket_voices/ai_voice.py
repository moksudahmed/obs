from playwright.sync_api import sync_playwright
import re
import json
import time
import random
import asyncio
import edge_tts
import os
import threading
from queue import Queue

# ---------------------------------------
# CONFIG
# ---------------------------------------
CREX_URL = "https://crex.com/scoreboard/10XZ/1PW/1st-Match/K/L/rcb-vs-srh-1st-match-indian-premier-league-2026/live"
OUTPUT_FILE = "C:/cricket_voices/score.json"
VOICE_FOLDER = "C:/cricket_voices/"
VOICE = "bn-BD-NabanitaNeural"
REFRESH_INTERVAL = 1  # seconds

# ---------------------------------------
# COMMENTARY
# ---------------------------------------
COMMENTARY2 = {
    "DOT": ["ডট বল", "দারুণ বল, কোনো রান নেই"],
    "SINGLE": ["এক রান নেওয়া হয়েছে"],
    "DOUBLE": ["দুই রান সম্পন্ন"],
    "TRIPLE": ["তিন রান নেওয়া হয়েছে"],
    "FOUR": ["চার! অসাধারণ শট"],
    "SIX": ["ছক্কা! বিশাল শট"],
    "WICKET": ["আউট! বড় উইকেট পড়েছে"],
    "OVER_COMPLETE": ["ওভার শেষ হয়েছে"],
    "WELCOME": ["""যারা এখনই লাইভে যুক্ত হয়েছেন, আপনাদের সবাইকে স্বাগতম!

আপনারা দেখছেন নিউজিল্যান্ড বনাম দক্ষিণ আফ্রিকার ম্যাচের লাইভ স্কোর আপডেট।
আমরা দিচ্ছি বল বাই বল আপডেট এবং সম্পূর্ণ বাংলা ধারাভাষ্য।

সঙ্গে থাকুন, সামনে আসছে আরও রোমাঞ্চকর মুহূর্ত!"""]
}
COMMENTARY = {

    "DOT": [
        "ডট বল, কোনো রান নেই।",
        "চমৎকার ডেলিভারি, ব্যাটসম্যান রান নিতে পারলেন না।",
        "দারুণ লাইন-লেন্থ, ব্যাটসম্যান চাপে।",
        "বলটা ভালোভাবে সামলেছেন, কিন্তু রান নেই।",
        "ডট বল, বোলারের দারুণ নিয়ন্ত্রণ দেখা যাচ্ছে।"
    ],

    "SINGLE": [
        "এক রান নেওয়া হয়েছে।",
        "সহজেই একটি রান সংগ্রহ করলেন।",
        "স্ট্রাইক ঘুরিয়ে দিলেন, এক রান।",
        "হালকা ট্যাপ করে একটি রান।",
        "দৌড়ে একটি রান সম্পন্ন।"
    ],

    "DOUBLE": [
        "দুই রান সম্পন্ন।",
        "দারুণ দৌড়ে দুই রান নিলেন।",
        "গ্যাপ খুঁজে বের করে দুই রান সংগ্রহ।",
        "ফিল্ডারের ফাঁক দিয়ে দুই রান।",
        "চমৎকার রানিং বিটুইন দ্য উইকেটস, দুই রান।"
    ],

    "TRIPLE": [
        "তিন রান নেওয়া হয়েছে।",
        "দারুণ দৌড়ে তিন রান সম্পন্ন।",
        "বড় শট না হলেও তিন রান পেলেন।",
        "ফিল্ডারদের ফাঁকি দিয়ে তিন রান।"
    ],

    "FOUR": [
        "চার! অসাধারণ শট!",
        "দারুণ টাইমিং, বল সোজা বাউন্ডারির বাইরে!",
        "চমৎকার কভার ড্রাইভ, চার রান!",
        "গ্যাপ খুঁজে নিয়েছেন, বল গড়িয়ে বাউন্ডারি!",
        "এটা থামানো সম্ভব ছিল না—চার!"
    ],

    "SIX": [
        "ছক্কা! বিশাল শট!",
        "বলটা সরাসরি গ্যালারিতে!",
        "কি দারুণ পাওয়ার, ছয় রান!",
        "দর্শকরা উপভোগ করছেন, দুর্দান্ত ছক্কা!",
        "একেবারে মাঠের বাইরে পাঠিয়ে দিলেন!"
    ],

    "WICKET": [
        "আউট! বড় উইকেট পড়েছে!",
        "বোলারের দারুণ সাফল্য, ব্যাটসম্যান ফিরে যাচ্ছেন।",
        "ক্যাচ! এবং আউট!",
        "এলবিডব্লিউ! আম্পায়ার আউট দিয়েছেন!",
        "ম্যাচে বড় টার্নিং পয়েন্ট!"
    ],

    "OVER_COMPLETE": [
        "ওভার শেষ হয়েছে।",
        "এই ওভার শেষে কিছুটা চাপ তৈরি হয়েছে।",
        "ওভার সমাপ্ত, এখন স্ট্র্যাটেজি বদলাতে পারে দল।",
        "ভালো একটি ওভার শেষ করলেন বোলার।"
    ],

    "WIDE": [
        "ওয়াইড বল, অতিরিক্ত এক রান।",
        "লাইন মিস করেছেন, ওয়াইড।",
        "খুব বাইরে বল, আম্পায়ারের ইশারা—ওয়াইড।"
    ],

    "NO_BALL": [
        "নো বল! ফ্রি হিট আসছে।",
        "ওভারস্টেপ করেছেন বোলার, নো বল।",
        "এটা নো বল, ব্যাটসম্যান পেলেন সুযোগ।"
    ],

    "FREE_HIT": [
        "এটি ফ্রি হিট!",
        "ব্যাটসম্যানের জন্য বড় সুযোগ, ফ্রি হিট বল।",
        "এই বলে আউট হওয়ার ভয় নেই, ফ্রি হিট।"
    ],

    "BYE": [
        "বাই রান নেওয়া হয়েছে।",
        "উইকেটকিপার মিস করেছেন, বাই রান।",
        "ব্যাটে লাগেনি, কিন্তু রান এসেছে।"
    ],

    "LEG_BYE": [
        "লেগ বাই, একটি রান।",
        "পায়ে লেগে বল সরে গেছে, রান নেওয়া হয়েছে।",
        "ব্যাটে লাগেনি, লেগ বাই হিসেবে গণনা।"
    ],

    "WELCOME": [
        """কি দারুণ ম্যাচ!

রয়্যাল চ্যালেঞ্জার্স বেঙ্গালুরু ৬ উইকেটে জয় পেয়েছে। 
চমৎকার রান তাড়া করে তারা নিশ্চিত করেছে দারুণ একটি জয়।

দারুণ ব্যাটিং পারফরম্যান্স, পরিকল্পিত খেলায় শেষ পর্যন্ত জয় তুলে নিল RCB। 
সানরাইজার্স হায়দরাবাদ চেষ্টা করলেও ম্যাচ নিজেদের পক্ষে আনতে পারেনি।

অভিনন্দন রয়্যাল চ্যালেঞ্জার্স বেঙ্গালুরুকে এই অসাধারণ জয়ের জন্য!""",

        """কি দারুণ ম্যাচ!

রয়্যাল চ্যালেঞ্জার্স বেঙ্গালুরু ৬ উইকেটে জয় পেয়েছে। 
চমৎকার রান তাড়া করে তারা নিশ্চিত করেছে দারুণ একটি জয়।

দারুণ ব্যাটিং পারফরম্যান্স, পরিকল্পিত খেলায় শেষ পর্যন্ত জয় তুলে নিল RCB। 
সানরাইজার্স হায়দরাবাদ চেষ্টা করলেও ম্যাচ নিজেদের পক্ষে আনতে পারেনি।

অভিনন্দন রয়্যাল চ্যালেঞ্জার্স বেঙ্গালুরুকে এই অসাধারণ জয়ের জন্য!"""
    ],

    "MATCH_RESULT": [
        "ম্যাচ শেষ! কি দারুণ লড়াই!",
        "খেলা শেষ, এক অসাধারণ ম্যাচের সমাপ্তি!",
        "শেষ পর্যন্ত দারুণ প্রতিদ্বন্দ্বিতা দেখলাম!",
        "এই ম্যাচটি ক্রিকেটপ্রেমীদের মনে থাকবে দীর্ঘদিন!"
    ]
}

# ---------------------------------------
# STATE
# ---------------------------------------
last_runs = None
last_wickets = None
last_over = None
last_ball = None
welcome_played = False

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

            # 🔁 Retry replace (Windows safe)
            for i in range(5):
                try:
                    if os.path.exists(final):
                        os.remove(final)  # remove old file first

                    os.rename(temp, final)  # safer than replace
                    break
                except PermissionError:
                    time.sleep(0.2)  # wait and retry
                except Exception as e:
                    print("Rename Error:", e)
                    break

        except Exception as e:
            print("🔊 Voice Error:", e)

        voice_queue.task_done()
        
def voice_worker2():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        event, text, final_path, temp_path = voice_queue.get()
        try:
            loop.run_until_complete(generate_voice(text, temp_path))
            os.replace(temp_path, final_path)
        except Exception as e:
            print("🔊 Voice Error:", e)
        voice_queue.task_done()

threading.Thread(target=voice_worker, daemon=True).start()

        
async def generate_voice(text, path):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(path)

def speak(event, text):
    print(f"🎙speak: {text}")
    os.makedirs(VOICE_FOLDER, exist_ok=True)
    final = os.path.join(VOICE_FOLDER, f"{event}.mp3")
    temp = final + ".tmp"
    voice_queue.put((event, text, final, temp))
    print(f"🎙 {event}: {text}")

# ---------------------------------------
# PARSE SCORE (ROBUST)
# ---------------------------------------
def parse_score2(text):
    """
    Extract runs, wickets, over, ball reliably from CREX text
    """
    text = text.replace("\n", " ")
    #print(text)
    # 1️⃣ Match runs-wickets first (first occurrence)
    match_score = re.search(r'\b(\d+)[-/](\d+)\b', text)
    if not match_score:
        return None

    runs = int(match_score.group(1))
    wickets = int(match_score.group(2))

    # 2️⃣ Match over.ball (first occurrence after runs-wickets)
    remaining_text = text[match_score.end():]
    match_over = re.search(r'(\d+)\.(\d+)', remaining_text)
    if match_over:
        over = int(match_over.group(1))
        ball = int(match_over.group(2))
    else:
        global last_over, last_ball
        over = last_over if last_over is not None else 0
        ball = last_ball if last_ball is not None else 0
    print("run:", runs)
    return runs, wickets, over, ball

def parse_score(text):
    """
    CREX format: '47-05.1'
    Means: runs=47, wickets=0, over=5, ball=1
    Pattern: {runs}-{wickets}{over}.{ball}
    """
    match = re.search(r'(\d+)-(\d)(\d+)\.([0-5])', text)
    if not match:
        return None

    runs    = int(match.group(1))
    wickets = int(match.group(2))  # single digit: 0-9
    over    = int(match.group(3))  # remaining digits after wicket
    ball    = int(match.group(4))  # decimal part, always 0-5

    return runs, wickets, over, ball


def clean_name(name):
    """
    Remove unwanted text before actual player name
    """
    # Keep only last 2–3 words (typical cricket name)
    words = name.strip().split()
    return " ".join(words[-2:])


def parse_batsmen(text):
    """
    Extract exactly 2 batsmen (clean & accurate)
    """

    # Normalize
    text = text.replace("\r", "").strip()

    # 🔥 Remove unwanted UI text before parsing
    remove_words = [
        "Match info", "Live", "Scorecard",
        "Commentary", "Over", "Projected Score"
    ]

    for word in remove_words:
        text = text.replace(word, "")

    # 👉 Core pattern (with + separator)
    pattern = r'''
        ([A-Z][a-zA-Z\s\.]+?)\s+
        (\d+)\s+\((\d+)\)\s*
        \+\s*
        ([A-Z][a-zA-Z\s\.]+?)\s+
        (\d+)\s+\((\d+)\)
    '''

    match = re.search(pattern, text, re.VERBOSE)

    if match:
        return [
            {
                "name": clean_name(match.group(1)),
                "runs": int(match.group(2)),
                "balls": int(match.group(3)),
            },
            {
                "name": clean_name(match.group(4)),
                "runs": int(match.group(5)),
                "balls": int(match.group(6)),
            }
        ]

    return []
# ---------------------------------------
# GET SCORE TEXT
# ---------------------------------------
def get_score_text(page):
    """
    Try multiple selectors to get full score (runs-wickets + overs)
    """
    selectors = [
        "div[class*='innings'] span[class*='score']",  # main score element
        "div[class*='score']",                         # fallback
    ]
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el:
                text = el.inner_text().strip()
                if text:
                    return text
        except:
            continue
    # final fallback
    try:
        return page.inner_text("body")
    except:
        return ""

# ---------------------------------------
# GET COMMENTARY
# ---------------------------------------
def get_commentary(page):
    try:
        el = page.query_selector("div[class*='commentary']")
        if el:
            return el.inner_text().lower()
    except:
        pass
    return ""

# ---------------------------------------
# DETECT EVENT
# ---------------------------------------
def detect_event2(runs, wickets, over, ball):
    global last_runs, last_wickets, last_over, last_ball

    if last_runs is None:
        last_runs, last_wickets, last_over, last_ball = runs, wickets, over, ball
        return "NONE"

    run_diff = runs - last_runs
    event = "NONE"

    if wickets > last_wickets:
        event = "WICKET"
    elif last_over is not None and over > last_over:
        event = "OVER_COMPLETE"
    elif over == last_over and ball != last_ball:
        if run_diff == 0:
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

    last_runs, last_wickets, last_over, last_ball = runs, wickets, over, ball
    return event
    
def detect_run2(runs):
        if runs == 0:
            event = "DOT"
        elif runs == 1:
            event = "SINGLE"
        elif runs == 2:
            event = "DOUBLE"
        elif runs == 3:
            event = "TRIPLE"
        elif runs == 4:
            event = "FOUR"
        elif runs >= 6:
            event = "SIX"
        return event

def detect_event3(runs, wickets, over, ball, commentary_text=""):
    """
    Detects the event for a single ball based on score changes and commentary.

    Parameters:
        runs (int): Total runs after current ball
        wickets (int): Total wickets after current ball
        over (int): Current over number
        ball (int): Ball number in the over (0-5)
        commentary_text (str): Optional commentary to detect wide/no ball

    Returns:
        str: Event type ("DOT", "SINGLE", "DOUBLE", "FOUR", "SIX", "WICKET", "OVER_COMPLETE", "WIDE", "NO_BALL", "NONE")
    """
    global last_runs, last_wickets, last_over, last_ball
    
    if last_runs is None:
        last_runs, last_wickets, last_over, last_ball = runs, wickets, over, ball
        return "NONE"
    
    run_diff = runs - last_runs
    event = "NONE"
    same_ball = (over == last_over and ball == last_ball)
    
    # ✅ WIDE DETECTION
    if same_ball and run_diff > 0:
        event = "WIDE"

    # Check for wickets
    if wickets > last_wickets:
        event = "WICKET"

    # Check if over completed
    elif last_over is not None and over > last_over:
        event = "OVER_COMPLETE"
        if run_diff > 0:       
            print(event)        
            event = detect_run(run_diff)
            print(event)

    # Check for a normal ball
    elif over == last_over and ball != last_ball:
        """if "wide" in commentary_text.lower():
            event = "WIDE"""
        if run_diff == 0 and ball == last_ball:
            event = "WIDE"
        elif "no ball" in commentary_text.lower():
            event = "NO_BALL"
        else:
            event = detect_run(run_diff)

    # Update last values
    last_runs, last_wickets, last_over, last_ball = runs, wickets, over, ball
    return event
    
def detect_event2(runs, wickets, over, ball):
    global last_runs, last_wickets, last_over, last_ball

    if last_runs is None:
        last_runs, last_wickets, last_over, last_ball = runs, wickets, over, ball
        return []

    run_diff = runs - last_runs
    events = []

    same_ball = (over == last_over and ball == last_ball)

    # ✅ WIDE DETECTION
    if same_ball and run_diff > 0:
        events.append("WIDE")

    else:
        # Ball event
        if wickets > last_wickets:
            events.append("WICKET")
        else:
            if run_diff == 0:
                events.append("DOT")
            elif run_diff == 1:
                events.append("SINGLE")
            elif run_diff == 2:
                events.append("DOUBLE")
            elif run_diff == 3:
                events.append("TRIPLE")
            elif run_diff == 4:
                events.append("FOUR")
            elif run_diff >= 6:
                events.append("SIX")

    # Over complete
    if last_over is not None and over > last_over:
        events.append("OVER_COMPLETE")

    last_runs, last_wickets, last_over, last_ball = runs, wickets, over, ball

    return events
  
def detect_run(run_diff):
    """
    Return run-based event
    """
    if run_diff == 0:
        return "DOT"
    elif run_diff == 1:
        return "SINGLE"
    elif run_diff == 2:
        return "DOUBLE"
    elif run_diff == 3:
        return "TRIPLE"
    elif run_diff == 4:
        return "FOUR"
    elif run_diff >= 6:
        return "SIX"
    return None


def detect_event(runs, wickets, over, ball, commentary_text=""):
    """
    MULTI-EVENT DETECTOR (FIXED)

    Returns:
        list → ["DOUBLE", "OVER_COMPLETE"]
    """
    global last_runs, last_wickets, last_over, last_ball

    # First call
    if last_runs is None:
        last_runs, last_wickets, last_over, last_ball = runs, wickets, over, ball
        return []

    run_diff = runs - last_runs
    events = []

    same_ball = (over == last_over and ball == last_ball)
    new_ball = (over == last_over and ball != last_ball)
    over_changed = (last_over is not None and over > last_over)

    commentary_text = commentary_text.lower()

    # ---------------------------------------
    # ✅ EXTRAS FIRST (WIDE / NO BALL)
    # ---------------------------------------
    if same_ball and run_diff > 0:
        if "no ball" in commentary_text:
            events.append("NO_BALL")
        else:
            events.append("WIDE")

    # ---------------------------------------
    # ✅ WICKET
    # ---------------------------------------
    if wickets > last_wickets:
        events.append("WICKET")

    # ---------------------------------------
    # ✅ RUN EVENT (for real ball OR last ball of over)
    # ---------------------------------------
    if run_diff > 0:
        run_event = detect_run(run_diff)
        if run_event:
            # avoid duplicate if already wide/no ball
            if run_event not in events:
                events.append(run_event)

    elif run_diff == 0 and new_ball:
        events.append("DOT")

    # ---------------------------------------
    # ✅ OVER COMPLETE (ALWAYS ADD SEPARATELY)
    # ---------------------------------------
    if over_changed:
        events.append("OVER_COMPLETE")

    # ---------------------------------------
    # UPDATE STATE
    # ---------------------------------------
    last_runs, last_wickets, last_over, last_ball = runs, wickets, over, ball

    return events
# ---------------------------------------
# WRITE JSON
# ---------------------------------------
def write_json(runs, wickets, over, ball, event):
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "runs": runs,
                "wickets": wickets,
                "over": over,
                "ball": ball,
                "event": event
            }, f, indent=4)
    except Exception as e:
        print("JSON Error:", e)

import random

def generate_score_commentary(runs, wickets, over):
    """
    Generate natural Bangla score commentary with variations
    """

    templates = [
        f"{over} ওভার শেষে স্কোর এখন {runs} রানে {wickets} উইকেট।",
        f"{over} ওভার শেষে দলের সংগ্রহ {runs} রান, হারিয়েছে {wickets} উইকেট।",
        f"{over} ওভার শেষে {runs} রান করেছে দলটি, তবে {wickets}টি উইকেট হারিয়েছে।",
        f"{over} ওভার শেষে স্কোরবোর্ডে {runs} রান, {wickets} উইকেট পড়ে গেছে।",
        f"{over} ওভার শেষে {runs}/{wickets} — ম্যাচ এখন বেশ জমে উঠেছে।",
        f"{runs} রান {wickets} উইকেটে, {over} ওভার শেষ।",
    ]

    # Optional pressure-style commentary
    pressure_templates = [
        f"{over} ওভার শেষে {runs}/{wickets}, দলটি কিছুটা চাপে রয়েছে।",
        f"{runs} রান হয়েছে, কিন্তু {wickets} উইকেট পড়ে যাওয়ায় ম্যাচে চাপ তৈরি হয়েছে।",
    ]

    # Randomly choose normal or pressure tone
    if wickets >= 5 and random.random() > 0.5:
        return random.choice(pressure_templates)

    return random.choice(templates)

def batsman_commentary(batsmen):
    if len(batsmen) == 2:
        b1, b2 = batsmen
        return f"{b1['name']} {b1['runs']} রানে খেলছেন, আর {b2['name']} করেছেন {b2['runs']} রান।"
# ---------------------------------------
# MAIN LOOP
# ---------------------------------------
def main():
    global welcome_played

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(CREX_URL)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2000)  # wait 2s for JS to render full score

        print("🚀 SYSTEM STARTED...")

        # WELCOME FIRST
        if not welcome_played:
            speak("WELCOME", random.choice(COMMENTARY["WELCOME"]))
            welcome_played = True
            time.sleep(1)

        while True:
            try:
                text = page.inner_text("body")

                score = parse_score(text)

                #text = get_score_text(page)
                #print("RAW:", text[:100])

                #score = parse_score(text)
                print("PARSED:", score)
                batsmen = parse_batsmen(text)

                for b in batsmen:
                    print(b)
                if not score:
                    time.sleep(REFRESH_INTERVAL)
                    continue

                runs, wickets, over, ball = score
                events = detect_event(runs, wickets, over, ball)
                  
                text = ""
                for event in events:
                    print("Event:", event)
                    write_json(runs, wickets, over, ball, event)
                    if event != "NONE":
                        line = random.choice(COMMENTARY[event])
                        if event == "OVER_COMPLETE":                        
                           line = generate_score_commentary(runs, wickets, over)
                        text = text + line
                        print("text:", text)
                        #line = random.choice(COMMENTARY.get(event, [""]))
                        if line:
                            speak(event, text)

            except Exception as e:
                print("MAIN ERROR:", e)
            time.sleep(REFRESH_INTERVAL)

# ---------------------------------------
if __name__ == "__main__":
    main()
