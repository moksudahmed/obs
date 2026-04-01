from playwright.sync_api import sync_playwright
import re
import json
import time
import random
import os
import threading
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Import custom modules
try:
    from commentry import generate_wicket_commentary, generate_winning_commentary, generate_event_commentary
except ImportError:
    print("⚠️ commentry module not found, using fallback")
    generate_wicket_commentary = lambda *args: "উইকেট!"
    generate_winning_commentary = lambda *args: "জয়!"
    generate_event_commentary = lambda *args: "দারুণ!"

from voice import speak

# =============================================
# CONFIGURATION
# =============================================
CREX_URL = "https://crex.com/cricket-live-score/dc-vs-lsg-5th-match-indian-premier-league-2026-match-updates-10Y3"
OUTPUT_FILE = "C:/cricket_voices/score.json"
REFRESH_INTERVAL = 1
VOICE_FOLDER = "C:/cricket_voices/"

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
MIN_TIME_BETWEEN_VOICE = 2

# =============================================
# UTILITY FUNCTIONS
# =============================================

def num_to_bn(n):
    """Convert number to Bangla words"""
    if n is None:
        return ""
    
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
    """Parse score from CREX format"""
    match = re.search(r'(\d+)-(\d)(\d+)\.([0-5])', text)
    if match:
        runs = int(match.group(1))
        wickets = int(match.group(2))
        over = int(match.group(3))
        ball = int(match.group(4))
        over_float = over + (ball / 10)
        return runs, wickets, over_float, ball
    
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
    
    remove_words = ["Match info", "Live", "Scorecard", "Commentary", "Over", "Projected Score"]
    for word in remove_words:
        text = text.replace(word, "")
    
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
            return False
        
        # Rate limiting
        if (current_time - last_spoken_time) < 1.5:
            return False
        
        try:
            speak(event, text)
            last_spoken_time = current_time
            last_spoken_event = event
            last_spoken_text = text
            return True
        except Exception as e:
            print(f"⚠️ Voice error: {e}")
            return False

def get_last_name(full_name):
    # Assuming format: "First Last"
    return full_name.split()[-1]
    
def generate_continuous_commentary(events: List[str], batsmen: List[Dict], runs: int, wickets: int, 
                                   over: float, team1: str = None, team2: str = None, 
                                   context: str = None, match_stats: Dict = None) -> str:
    """Generate intelligent, human-like cricket commentary"""
    parts = []
    
    if match_stats is None:
        match_stats = {
            'consecutive_boundaries': 0,
            'consecutive_dots': 0,
            'runs_in_over': 0,
            'wickets_in_over': 0,
            'match_phase': 'powerplay' if over <= 6 else 'middle' if over <= 15 else 'death'
        }
    
    # Wicket commentary
    if "WICKET" in events:
        try:
            wicket_text = generate_wicket_commentary(runs, wickets, over, 
                                                     get_last_name(batsmen[0]['name']) if batsmen else None)
            parts.append(wicket_text)
        except:
            parts.append("আউট! উইকেট পতন!")
        
        if wickets <= 3:
            parts.append("দলীয় সংগ্রহে বড় ধাক্কা!")
        elif wickets <= 6:
            parts.append("মিডল অর্ডার ভেঙে পড়ল!")
        else:
            parts.append("টেইল এন্ডার্স এসে গেছেন!")
    
    # Scoring events
    scoring_events = ["SIX", "FOUR", "DOUBLE", "SINGLE", "DOT"]
    for event in scoring_events:
        if event in events:
            try:
                base = generate_event_commentary([event])
            except:
                base = {"SIX": "ছক্কা!", "FOUR": "চার!", "DOUBLE": "দুই রান!", 
                        "SINGLE": "এক রান!", "DOT": "ডট বল!"}.get(event, "")
            
            if event == "SIX":
                parts.append(f"{base} দর্শকরা উন্মাদ!")
                match_stats['consecutive_boundaries'] += 1
                if match_stats['consecutive_boundaries'] >= 2:
                    parts.append("লাগাতার দ্বিতীয় ছক্কা!")
            elif event == "FOUR":
                parts.append(base)
                match_stats['consecutive_boundaries'] += 1
            elif event == "DOT":
                match_stats['consecutive_dots'] += 1
                if match_stats['consecutive_dots'] == 1:
                    parts.append(base)
                elif match_stats['consecutive_dots'] >= 2:
                    parts.append(f"টানা {num_to_bn(match_stats['consecutive_dots'])} ডট বল!")
            else:
                parts.append(base)
                match_stats['consecutive_boundaries'] = 0
                match_stats['consecutive_dots'] = 0
            break
    
    # Extras
    if "WIDE" in events:
        parts.append("ওয়াইড বল! অতিরিক্ত রান।")
    if "NO_BALL" in events:
        parts.append("নো বল! ফ্রি হিট আসছে।")
    
    # Batsman status
    if batsmen:
        for i, batsman in enumerate(batsmen[:2]):
            if i == 0:
                parts.append(f"{get_last_name(batsmen[0]['name'])} {num_to_bn(batsman['runs'])} রানে।")
            else:
                parts.append(f"অন্য প্রান্তে {get_last_name(batsmen[0]['name'])} {num_to_bn(batsman['runs'])} রানে।")
    
    # Over summary
    if "OVER_COMPLETE" in events:
        over_bn = num_to_bn(int(over))
        parts.append(f"{over_bn} ওভার শেষ। স্কোর {num_to_bn(runs)} {wickets} উইকেটে।")
    
    return " ".join(parts)


# =============================================
# WELCOME MESSAGE
# =============================================

WELCOME_MESSAGE = """নতুন যারা এখনই লাইভে যুক্ত হয়েছেন, আপনাদের সবাইকে স্বাগতম!

ম্যাচের সর্বশেষ আপডেট জানিয়ে দিচ্ছি—
লখনৌ সুপার জায়ান্টস তাদের ইনিংসে ১৮.৪ ওভারে ১০ উইকেট হারিয়ে ১৪১ রান সংগ্রহ করেছে।

এই মুহূর্তে চলছে ইনিংস ব্রেক।

শুরুর দিকে কিছু ভালো ব্যাটিং থাকলেও,
শেষ দিকে দ্রুত উইকেট হারিয়ে বড় স্কোর গড়তে পারেনি লখনৌ।

এখন দিল্লি ক্যাপিটালস নামবে এই লক্ষ্য তাড়া করতে,
এবং ম্যাচ কোন দিকে মোড় নেয়, সেটাই দেখার বিষয়।

সঙ্গে থাকুন, কারণ দ্বিতীয় ইনিংসে অপেক্ষা করছে আরও উত্তেজনা,
আমরা দিচ্ছি বল বাই বল আপডেট এবং সম্পূর্ণ বাংলা কমেন্ট্রি!

কোথাও যাবেন না!"""


# =============================================
# MAIN FUNCTION
# =============================================

def cleanup_temp_files():
    """Remove temporary files from previous runs"""
    try:
        for file in os.listdir(VOICE_FOLDER):
            if any(x in file for x in ['.tmp', '_temp_', '.backup']):
                try:
                    os.remove(os.path.join(VOICE_FOLDER, file))
                except:
                    pass
    except:
        pass


def main():
    global welcome_played, last_runs, last_wickets, last_over, last_ball
    
    # Clean up temp files
    cleanup_temp_files()
    
    match_stats = {
        'consecutive_boundaries': 0,
        'consecutive_dots': 0,
        'runs_in_over': 0,
        'wickets_in_over': 0,
        'match_phase': 'powerplay'
    }
    
    last_runs = None
    last_wickets = None
    last_over = None
    last_ball = None
    
    # Play welcome message
    if not welcome_played:
        speak("WELCOME", WELCOME_MESSAGE)
        welcome_played = True
        time.sleep(3)
    
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
            
            last_state = {
                'runs': 0, 'wickets': 0, 'over': 0, 'ball': 0,
                'batsmen': [], 'last_commentary': ""
            }
            processed_events = {}
            
            while True:
                try:
                    text = page.inner_text("body")
                    score = parse_score(text)
                    
                    if not score:
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
                    event_key = f"{runs}_{wickets}_{over}_{ball}"
                    batsmen = parse_batsmen(text)
                    
                    # Get status message
                    status_message = ""
                    for line in text.splitlines():
                        if any(k in line.lower() for k in ['wide', 'no ball', 'out', 'four', 'six']):
                            status_message = line
                            break
                    
                    events = detect_event(runs, wickets, over, ball, status_message)
                    
                    if not events:
                        time.sleep(REFRESH_INTERVAL)
                        continue
                    
                    if event_key in processed_events and (time.time() - processed_events[event_key]) < 3:
                        time.sleep(REFRESH_INTERVAL)
                        continue
                    
                    # Update match stats
                    if over != last_state['over']:
                        match_stats['runs_in_over'] = 0
                        match_stats['wickets_in_over'] = 0
                    else:
                        if last_state['runs'] > 0:
                            match_stats['runs_in_over'] += (runs - last_state['runs'])
                        match_stats['wickets_in_over'] += (wickets - last_state['wickets'])
                    
                    # Generate commentary
                    line = generate_continuous_commentary(
                        events=events, batsmen=batsmen, runs=runs, wickets=wickets,
                        over=over, context=status_message, match_stats=match_stats
                    )
                    
                    if line and line != last_state['last_commentary']:
                        print(f"\n🎙 {line}")
                        print(f"📊 স্কোর: {runs}/{wickets} | ওভার: {over:.1f}")
                        print("-" * 60)
                        
                        write_json(runs, wickets, over, ball, events[0])
                        safe_speak(events[0], line)
                        
                        last_state['last_commentary'] = line
                        processed_events[event_key] = time.time()
                        
                        # Clean old events
                        if len(processed_events) > 50:
                            oldest = min(processed_events.keys(), key=lambda k: processed_events[k])
                            del processed_events[oldest]
                    
                    last_state.update({'runs': runs, 'wickets': wickets, 'over': over, 
                                      'ball': ball, 'batsmen': batsmen})
                    
                except Exception as e:
                    print(f"⚠️ Error: {e}")
                
                time.sleep(REFRESH_INTERVAL)
                
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
