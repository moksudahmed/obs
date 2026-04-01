from playwright.sync_api import sync_playwright
import re
import json
import time
import random
import os
import threading
import queue
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Import your custom modules
from commentry import generate_wicket_commentary, generate_winning_commentary, generate_event_commentary, generate_toss_commentary
from voice import speak

# =============================================
# CONFIGURATION
# =============================================
CREX_URL = "https://crex.com/cricket-live-score/dub-vs-emb-5th-match-emirates-d50-tournament-2026-match-updates-11CD"
OUTPUT_FILE = "C:/cricket_voices/score.json"
REFRESH_INTERVAL = 1

# Global state variables
last_runs = None
last_wickets = None
last_over = None
last_ball = None
welcome_played = False

# Voice queue management
voice_lock = threading.Lock()
last_spoken_time = 0
last_spoken_event = None
last_spoken_text = None
MIN_TIME_BETWEEN_VOICE = 2  # Minimum seconds between voice outputs

# =============================================
# ENHANCED UTILITY FUNCTIONS
# =============================================

def num_to_bn(n):
    """Convert number to Bangla words with better formatting"""
    if n is None:
        return ""
    
    # Handle decimal overs
    if isinstance(n, float):
        over_part = int(n)
        ball_part = int((n - over_part) * 10) if (n - over_part) > 0 else 0
        if ball_part > 0:
            return f"{num_to_bn(over_part)} দশমিক {num_to_bn(ball_part)}"
    
    bn_digits = {
        0: "শূন্য", 1: "এক", 2: "দুই", 3: "তিন", 4: "চার",
        5: "পাঁচ", 6: "ছয়", 7: "সাত", 8: "আট", 9: "নয়",
        10: "দশ", 11: "এগারো", 12: "বারো", 13: "তেরো", 14: "চৌদ্দ",
        15: "পনেরো", 16: "ষোল", 17: "সতেরো", 18: "আঠারো", 19: "উনিশ",
        20: "বিশ", 21: "একুশ", 22: "বাইশ", 23: "তেইশ", 24: "চব্বিশ",
        25: "পঁচিশ", 30: "ত্রিশ", 40: "চল্লিশ", 50: "পঞ্চাশ",
        100: "একশ", 200: "দুইশ", 1000: "হাজার"
    }
    
    if n in bn_digits:
        return bn_digits[n]
    
    # Handle larger numbers
    if n < 100:
        tens = (n // 10) * 10
        ones = n % 10
        if ones == 0:
            return bn_digits.get(tens, str(n))
        return f"{bn_digits.get(tens, str(tens))} {bn_digits.get(ones, str(ones))}"
    
    return str(n)


def format_run_rate(runs, overs):
    """Calculate and format run rate"""
    if overs == 0:
        return "০"
    rr = runs / overs
    return f"{rr:.1f}".replace('.', ' দশমিক ')


def parse_score(text: str) -> Optional[Tuple[int, int, float, int]]:
    """Parse score from CREX format: '47-05.1'"""
    # Try to find pattern like "47-05.1" or "150-3 15.2"
    match = re.search(r'(\d+)-(\d)(\d+)\.([0-5])', text)
    if match:
        runs = int(match.group(1))
        wickets = int(match.group(2))
        over = int(match.group(3))
        ball = int(match.group(4))
        over_float = over + (ball / 10)
        return runs, wickets, over_float, ball
    
    # Alternative pattern
    match = re.search(r'(\d+)-(\d+)\s+(\d+)\.([0-5])', text)
    if match:
        runs = int(match.group(1))
        wickets = int(match.group(2))
        over = int(match.group(3))
        ball = int(match.group(4))
        over_float = over + (ball / 10)
        return runs, wickets, over_float, ball
    
    return None


def parse_batsmen(text: str) -> List[Dict]:
    """Extract batsmen information"""
    text = text.replace("\r", "").strip()
    
    # Remove unwanted UI text
    remove_words = ["Match info", "Live", "Scorecard", "Commentary", "Over", "Projected Score"]
    for word in remove_words:
        text = text.replace(word, "")
    
    # Pattern for batsmen: "Name 45 (30) + Name 23 (15)"
    pattern = r'([A-Z][a-zA-Z\s\.]+?)\s+(\d+)\s+\((\d+)\)\s*\+\s*([A-Z][a-zA-Z\s\.]+?)\s+(\d+)\s+\((\d+)\)'
    match = re.search(pattern, text, re.VERBOSE)
    
    if match:
        def clean_name(name):
            words = name.strip().split()
            return " ".join(words[-2:]) if len(words) > 2 else name
        
        return [
            {"name": clean_name(match.group(1)), "runs": int(match.group(2)), "balls": int(match.group(3))},
            {"name": clean_name(match.group(4)), "runs": int(match.group(5)), "balls": int(match.group(6))}
        ]
    
    # Try simpler pattern
    pattern2 = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(\d+)\s*\(\s*(\d+)\s*\)'
    matches = re.findall(pattern2, text)
    batsmen = []
    for name, runs, balls in matches[:2]:
        batsmen.append({'name': name.strip(), 'runs': int(runs), 'balls': int(balls)})
    
    return batsmen


def parse_winning_info(text: str) -> Dict:
    """Parse winning information"""
    match = re.search(r'([A-Za-z\s]+?)\s+won by\s+(\d+)\s+(wickets|runs)', text.lower())
    if match:
        return {
            'team': match.group(1).strip().title(),
            'margin': int(match.group(2)),
            'type': match.group(3)
        }
    return {'team': None, 'margin': None, 'type': None}


def detect_event(runs: int, wickets: int, over: float, ball: int, commentary: str) -> List[str]:
    """Detect events from score change and commentary"""
    global last_runs, last_wickets, last_over, last_ball
    
    if last_runs is None:
        last_runs, last_wickets, last_over, last_ball = runs, wickets, over, ball
        return []
    
    events = []
    commentary_lower = commentary.lower()
    
    # Wicket detection
    if wickets > last_wickets:
        events.append("WICKET")
        if "bowled" in commentary_lower:
            events.append("BOWLED")
        elif "caught" in commentary_lower:
            events.append("CATCH")
        elif "lbw" in commentary_lower:
            events.append("LBW")
        elif "run out" in commentary_lower:
            events.append("RUN_OUT")
        elif "stumped" in commentary_lower:
            events.append("STUMPED")
    
    # Run detection
    run_diff = runs - last_runs
    if run_diff > 0:
        if "wide" in commentary_lower:
            events.append("WIDE")
        elif "no ball" in commentary_lower:
            events.append("NO_BALL")
        elif run_diff >= 6:
            events.append("SIX")
        elif run_diff == 4:
            events.append("FOUR")
        elif run_diff == 2:
            events.append("DOUBLE")
        elif run_diff == 1:
            events.append("SINGLE")
    elif run_diff == 0 and (over > last_over or (over == last_over and ball != last_ball)):
        events.append("DOT")
    
    # Over complete
    if over > last_over:
        events.append("OVER_COMPLETE")
    
    # Update state
    last_runs, last_wickets, last_over, last_ball = runs, wickets, over, ball
    
    return events


def write_json(runs: int, wickets: int, over: float, ball: int, event: str):
    """Save current state to JSON"""
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "runs": runs,
                "wickets": wickets,
                "over": over,
                "ball": ball,
                "event": event,
                "timestamp": datetime.now().isoformat()
            }, f, indent=4)
    except Exception as e:
        print(f"JSON Error: {e}")


def safe_speak(event, text):
    """Thread-safe speak function with deduplication and rate limiting"""
    global last_spoken_time, last_spoken_event, last_spoken_text
    
    with voice_lock:
        current_time = time.time()
        
        # Don't speak if it's the same as last spoken
        if text == last_spoken_text:
            print(f"🔄 Skipping duplicate commentary: {text[:50]}...")
            return False
        
        # Don't speak if it's the same event within MIN_TIME_BETWEEN_VOICE seconds
        if event == last_spoken_event and (current_time - last_spoken_time) < MIN_TIME_BETWEEN_VOICE:
            print(f"⏱️ Rate limiting: Skipping {event} (last spoken {current_time - last_spoken_time:.1f}s ago)")
            return False
        
        # Don't speak if too frequent (regardless of event)
        if (current_time - last_spoken_time) < 1.5:  # At least 1.5 seconds between any speech
            print(f"⏱️ Too frequent: Skipping {event} (last spoken {current_time - last_spoken_time:.1f}s ago)")
            return False
        
        try:
            speak(event, text)
            last_spoken_time = current_time
            last_spoken_event = event
            last_spoken_text = text
            print(f"🔊 Spoken: {event}")
            return True
        except Exception as e:
            print(f"⚠️ Voice error: {e}")
            return False


# =============================================
# ENHANCED COMMENTARY GENERATION
# =============================================

def generate_continuous_commentary(events: List[str], batsmen: List[Dict], runs: int, wickets: int, 
                                   over: float, team1: str = None, team2: str = None, 
                                   context: str = None, match_stats: Dict = None) -> str:
    """
    Generate intelligent, human-like cricket commentary with full match context
    """
    parts = []
    
    # Initialize match stats
    if match_stats is None:
        match_stats = {
            'consecutive_boundaries': 0,
            'consecutive_dots': 0,
            'runs_in_over': 0,
            'wickets_in_over': 0,
            'last_wicket_type': None,
            'powerplay_active': over <= 6 if over else False,
            'death_overs': over >= 15 if over else False
        }
    
    # =============================================
    # 1️⃣ WICKET COMMENTARY (Highest Priority)
    # =============================================
    if "WICKET" in events:
        # Try to get wicket commentary from your module
        try:
            wicket_text = generate_wicket_commentary(runs, wickets, over, 
                                                     batsmen[0]['name'] if batsmen else None)
            parts.append(wicket_text)
        except:
            # Fallback wicket commentary
            if "BOWLED" in events:
                parts.append("বোল্ড! উইকেট ভেঙে উড়ে গেল! অসাধারণ ডেলিভারি।")
            elif "CATCH" in events:
                parts.append("ক্যাচ! ফিল্ডার দারুণ ক্যাচ নিলেন। ব্যাটসম্যান ফিরে যাচ্ছেন।")
            else:
                parts.append("আউট! উইকেট পতন! ব্যাটসম্যান সাজঘরের পথে।")
        
        # Add wicket context
        if wickets <= 3:
            parts.append("দলীয় সংগ্রহে এই উইকেটটা বড় ধাক্কা!")
        elif wickets <= 6:
            parts.append("মিডল অর্ডার ভেঙে পড়ল! চাপ বাড়ছে ব্যাটিং দলের উপর।")
        else:
            parts.append("টেইল এন্ডার্স এসে গেছেন! শেষ উইকেটের লড়াই দেখার মতো।")
    
    # =============================================
    # 2️⃣ SCORING EVENTS with Context
    # =============================================
    scoring_events = ["SIX", "FOUR", "DOUBLE", "SINGLE", "DOT"]
    
    for event in scoring_events:
        if event in events:
            # Get base commentary
            try:
                base_commentary = generate_event_commentary([event])
            except:
                # Fallback commentary
                if event == "SIX":
                    base_commentary = "বাহ! বিশাল ছক্কা! বলটা গ্যালারিতে চলে গেল।"
                elif event == "FOUR":
                    base_commentary = "চার! বলটা বাউন্ডারি লাইন অতিক্রম করল।"
                elif event == "DOUBLE":
                    base_commentary = "দুই রান! দ্রুত দৌড়ে স্কোর বাড়ালেন।"
                elif event == "SINGLE":
                    base_commentary = "এক রান! স্ট্রাইক রোটেট করে নিলেন।"
                else:
                    base_commentary = "ডট বল! বোলার দারুণ বল করেছেন।"
            
            # Add context based on match situation
            if event == "SIX":
                parts.append(f"{base_commentary} দর্শকরা উন্মাদ! এটা ম্যাচের মোড় ঘুরিয়ে দিতে পারে।")
                match_stats['consecutive_boundaries'] += 1
                match_stats['consecutive_dots'] = 0
                
                if match_stats['consecutive_boundaries'] >= 2:
                    parts.append("লাগাতার দ্বিতীয় ছক্কা! ব্যাটসম্যান দারুণ ফর্মে আছেন!")
                
            elif event == "FOUR":
                parts.append(base_commentary)
                match_stats['consecutive_boundaries'] += 1
                match_stats['consecutive_dots'] = 0
                
                if match_stats['consecutive_boundaries'] >= 3:
                    parts.append("টানা তৃতীয় বাউন্ডারি! বোলারকে রক্ষা করার কেউ নেই!")
                    
            elif event == "DOUBLE":
                parts.append(base_commentary)
                match_stats['consecutive_boundaries'] = 0
                match_stats['consecutive_dots'] = 0
                
            elif event == "SINGLE":
                parts.append(base_commentary)
                match_stats['consecutive_boundaries'] = 0
                match_stats['consecutive_dots'] = 0
                
            elif event == "DOT":
                match_stats['consecutive_dots'] += 1
                match_stats['consecutive_boundaries'] = 0
                
                if match_stats['consecutive_dots'] == 1:
                    parts.append(base_commentary)
                elif match_stats['consecutive_dots'] == 2:
                    parts.append(f"টানা দ্বিতীয় ডট বল! ব্যাটসম্যানের উপর চাপ বাড়ছে।")
                elif match_stats['consecutive_dots'] >= 3:
                    parts.append(f"টানা {num_to_bn(match_stats['consecutive_dots'])} ডট বল! মেডেন ওভারের সম্ভাবনা!")
            
            break  # Only one scoring event per ball
    
    # =============================================
    # 3️⃣ EXTRAS with Detailed Analysis
    # =============================================
    if "WIDE" in events:
        try:
            parts.append(generate_event_commentary(["WIDE"]))
        except:
            parts.append("ওয়াইড! বলটা ব্যাটসম্যানের নাগালের বাইরে। এক্সট্রা রান।")
        parts.append("বোলার লাইন ঠিক রাখতে পারলেন না। অতিরিক্ত রান দিয়ে বসলেন।")
        
    if "NO_BALL" in events:
        try:
            parts.append(generate_event_commentary(["NO_BALL"]))
        except:
            parts.append("নো বল! বোলার ফ্রন্ট ফুট লাইন ক্রস করেছেন।")
        parts.append("পরের বলে ফ্রি হিট! ব্যাটসম্যান বড় শটের সুযোগ পাচ্ছেন।")
    
    # =============================================
    # 4️⃣ INTELLIGENT BATSMAN STATUS
    # =============================================
    if batsmen:
        batsman_status = []
        
        for i, batsman in enumerate(batsmen[:2]):
            runs_bn = num_to_bn(batsman['runs'])
            balls_bn = num_to_bn(batsman.get('balls', 0))
            
            # Strike rate calculation
            strike_rate = (batsman['runs'] / max(batsman.get('balls', 1), 1)) * 100
            strike_rate_bn = f"{strike_rate:.1f}".replace('.', ' দশমিক ')
            
            if i == 0:  # On-strike batsman
                if batsman['runs'] < 10:
                    status = f"{batsman['name']} {runs_bn} রানে সাবধানে খেলছেন।"
                elif batsman['runs'] < 30:
                    status = f"{batsman['name']} {runs_bn} রানে দারুণ ছন্দে আছেন।"
                elif batsman['runs'] < 50:
                    status = f"{batsman['name']} {runs_bn} রানে ফিফটির দিকে এগোচ্ছেন।"
                elif batsman['runs'] < 100:
                    status = f"{batsman['name']} {runs_bn} রানে ফিফটি করেছেন! সেঞ্চুরির দিকে তাকিয়ে।"
                else:
                    status = f"{batsman['name']} {runs_bn} রানে সেঞ্চুরি করেছেন! অসাধারণ ইনিংস!"
                
                # Add strike rate context
                if strike_rate > 100:
                    status += f" স্ট্রাইক রেট {strike_rate_bn}! আগ্রাসী ব্যাটিং।"
                elif strike_rate < 70 and batsman['balls'] > 10:
                    status += f" স্ট্রাইক রেট {strike_rate_bn}। কিছুটা ধীর।"
                    
                batsman_status.append(status)
                
            else:  # Non-strike batsman
                if batsman['runs'] < 10:
                    status = f"অন্য প্রান্তে {batsman['name']} {runs_bn} রানে।"
                else:
                    status = f"{batsman['name']} {runs_bn} রানে ব্যাট করছেন।"
                batsman_status.append(status)
        
        if batsman_status:
            parts.append(" ".join(batsman_status))
    
    # =============================================
    # 5️⃣ OVER SUMMARY with Detailed Stats
    # =============================================
    if "OVER_COMPLETE" in events:
        over_bn = num_to_bn(int(over))
        runs_bn = num_to_bn(runs)
        wickets_bn = num_to_bn(wickets)
        
        # Calculate run rate
        current_rr = format_run_rate(runs, over)
        
        # Different over summaries based on performance
        if match_stats.get('runs_in_over', 0) == 0:
            over_comment = f"{over_bn} ওভার শেষ। স্কোর {runs_bn}/{wickets_bn}। মেডেন ওভার! অসাধারণ বোলিং।"
        elif match_stats.get('wickets_in_over', 0) > 0:
            over_comment = f"{over_bn} ওভার শেষ। {match_stats['wickets_in_over']} উইকেট পতন! স্কোর {runs_bn}/{wickets_bn}। ম্যাচের মোড় ঘুরে গেল!"
        elif match_stats.get('runs_in_over', 0) >= 15:
            over_comment = f"{over_bn} ওভার শেষ। এই ওভারে {num_to_bn(match_stats['runs_in_over'])} রান! ব্যাটিং দারুণ ছন্দে।"
        else:
            over_comment = f"{over_bn} ওভার শেষ। স্কোর {runs_bn}/{wickets_bn}। বর্তমান রান রেট {current_rr}।"
        
        parts.append(over_comment)
        
        # Add strategic comment based on match phase
        if over <= 6:
            parts.append("পাওয়ারপ্লেতে এই সংগ্রহ বেশ ভালো।")
        elif over <= 15:
            parts.append("মিডল ওভারে এখন স্ট্রাইক রোটেট করে এগোতে হবে।")
        elif over >= 15:
            parts.append("ডেথ ওভারে বড় শট মারার সময় এসেছে!")
    
    # =============================================
    # 6️⃣ ADD DYNAMIC CONNECTIVES FOR NATURAL FLOW
    # =============================================
    connectors = [
        "এছাড়াও", "পাশাপাশি", "এদিকে", "অন্যদিকে", 
        "ঠিক তখনই", "তারপরেই", "হঠাৎ করে"
    ]
    
    # Combine parts with natural flow
    if len(parts) > 1:
        final_parts = []
        for i, part in enumerate(parts):
            if i > 0 and not part.startswith("যারা"):
                connector = random.choice(connectors)
                final_parts.append(f"{connector} {part}")
            else:
                final_parts.append(part)
        return " ".join(final_parts)
    
    return " ".join(parts) if parts else ""


# =============================================
# MAIN FUNCTION
# =============================================

def main():
    global welcome_played, last_runs, last_wickets, last_over, last_ball
    
    # Match statistics tracker
    match_stats = {
        'consecutive_boundaries': 0,
        'consecutive_dots': 0,
        'runs_in_over': 0,
        'wickets_in_over': 0,
        'last_over_runs': 0,
        'powerplay_active': True,
        'death_overs_started': False,
        'match_phase': 'powerplay',
        'total_runs_last_5_overs': [],
        'wicket_fall_times': [],
        'partnership_runs': 0,
        'last_batsman_out': None
    }
    
    # Reset global state
    last_runs = None
    last_wickets = None
    last_over = None
    last_ball = None
    
    # Track processed events to avoid duplicates
    processed_events = {}
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            print(f"🌐 Navigating to: {CREX_URL}")
            page.goto(CREX_URL)
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(2000)
            
            print("🚀 CRICKET COMMENTARY SYSTEM ACTIVATED")
            print("=" * 60)
            
            # Track last state for continuous flow
            last_state = {
                'runs': 0,
                'wickets': 0,
                'over': 0,
                'ball': 0,
                'batsmen': [],
                'last_commentary': ""
            }
            
            while True:
                try:
                    # =========================================
                    # FETCH AND PARSE DATA
                    # =========================================
                    text = page.inner_text("body")
                    score = parse_score(text)
                    
                    if not score:
                        # Check for match end
                        info = parse_winning_info(text)
                        if info['team']:
                            try:
                                line = generate_winning_commentary(info["team"], info["margin"], info["type"])
                            except:
                                line = f"{info['team']} {info['margin']} {info['type']} এ জয়লাভ করলো!"
                            safe_speak("MATCH_END", line)
                            print(f"🏆 {line}")
                        time.sleep(REFRESH_INTERVAL)
                        continue
                    
                    runs, wickets, over, ball = score
                    
                    # Create a unique event key to detect duplicates
                    event_key = f"{runs}_{wickets}_{over}_{ball}"
                    
                    # Parse batsmen and commentary
                    batsmen = parse_batsmen(text)
                    lines = text.splitlines()
                    
                    # Intelligent status message extraction
                    status_message = ""
                    for line in lines:
                        if any(keyword in line.lower() for keyword in ['wide', 'no ball', 'out', 'four', 'six', 'catch', 'bowled']):
                            status_message = line
                            break
                    
                    # =========================================
                    # EVENT DETECTION WITH CONTEXT
                    # =========================================
                    events = detect_event(runs, wickets, over, ball, status_message)
                    
                    # Skip if no events or already processed
                    if not events:
                        time.sleep(REFRESH_INTERVAL)
                        continue
                    
                    # Check if this exact event was recently processed
                    if event_key in processed_events and (time.time() - processed_events[event_key]) < 3:
                        print(f"🔄 Skipping duplicate event: {events[0]} at {event_key}")
                        time.sleep(REFRESH_INTERVAL)
                        continue
                    
                    # Update match stats for current over
                    if over != last_state['over']:
                        # New over started
                        match_stats['runs_in_over'] = 0
                        match_stats['wickets_in_over'] = 0
                        
                        # Update match phase
                        if over <= 6:
                            match_stats['match_phase'] = 'powerplay'
                        elif over <= 15:
                            match_stats['match_phase'] = 'middle'
                        else:
                            match_stats['match_phase'] = 'death'
                            if not match_stats['death_overs_started']:
                                match_stats['death_overs_started'] = True
                                safe_speak("DEATH_OVERS", "ডেথ ওভার শুরু! শেষ দিকে বড় শটের আশায় দর্শকরা।")
                    else:
                        # Same over, accumulate stats
                        if last_state['runs'] > 0:
                            match_stats['runs_in_over'] += (runs - last_state['runs'])
                        match_stats['wickets_in_over'] += (wickets - last_state['wickets'])
                    
                    # Track partnership
                    if wickets > last_state['wickets']:
                        # Wicket fell - end partnership
                        if batsmen:
                            match_stats['last_batsman_out'] = batsmen[0]['name'] if batsmen else "ব্যাটসম্যান"
                        match_stats['partnership_runs'] = 0
                    else:
                        # Add runs to partnership
                        if last_state['runs'] > 0:
                            match_stats['partnership_runs'] += (runs - last_state['runs'])
                    
                    # =========================================
                    # GENERATE CONTEXTUAL COMMENTARY
                    # =========================================
                    # Generate enhanced commentary
                    line = generate_continuous_commentary(
                        events=events,
                        batsmen=batsmen,
                        runs=runs,
                        wickets=wickets,
                        over=over,
                        team1=None,
                        team2=None,
                        context=status_message,
                        match_stats=match_stats
                    )
                    
                    # =========================================
                    # OUTPUT WITH SMART DE-DUPLICATION
                    # =========================================
                    if line and line != last_state['last_commentary']:
                        print(f"\n🎙 {line}")
                        print(f"📊 স্কোর: {runs}/{wickets} | ওভার: {over:.1f} | ইভেন্ট: {events[0]}")
                        print("-" * 60)
                        
                        # Save to JSON
                        write_json(runs, wickets, over, ball, events[0])
                        
                        # Speak the commentary with rate limiting
                        safe_speak(events[0], line)
                        
                        # Update last state
                        last_state['last_commentary'] = line
                        
                        # Mark this event as processed
                        processed_events[event_key] = time.time()
                        
                        # Clean old processed events (keep last 50)
                        if len(processed_events) > 50:
                            oldest_key = min(processed_events.keys(), key=lambda k: processed_events[k])
                            del processed_events[oldest_key]
                    
                    # Update state for next iteration
                    last_state.update({
                        'runs': runs,
                        'wickets': wickets,
                        'over': over,
                        'ball': ball,
                        'batsmen': batsmen
                    })
                    
                except Exception as e:
                    print(f"⚠️ Error in main loop: {e}")
                    import traceback
                    traceback.print_exc()
                
                time.sleep(REFRESH_INTERVAL)
                
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


# =============================================
# ENTRY POINT
# =============================================

if __name__ == "__main__":
    main()