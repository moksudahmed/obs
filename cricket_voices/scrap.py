from playwright.sync_api import sync_playwright
import re
import json
import time

# ---------------------------------------
# CONFIG
# ---------------------------------------

CREX_URL = "https://crex.com/scoreboard/10VV/2F5/2nd-Match/1ET/1ER/cc-vs-gw-2nd-match-ayodhya-premier-league-2026/live"

OUTPUT_FILE = "C:/cricket_voices/score.json"

REFRESH_INTERVAL = 3


# ---------------------------------------
# STATE VARIABLES
# ---------------------------------------

last_score = None
last_wickets = None
last_over = None
last_ball = None
last_commentary = ""
free_hit_active = False


# ---------------------------------------
# SCORE PARSER
# ---------------------------------------

def parse_score(page_text):

    compressed = re.search(r'(\d+)-(\d)(\d+)\.(\d)', page_text)

    if compressed:
        return (
            int(compressed.group(1)),
            int(compressed.group(2)),
            int(compressed.group(3)),
            int(compressed.group(4))
        )

    score_match = re.search(r'(\d+)\s*-\s*(\d+)', page_text)
    over_match = re.search(r'(\d+)\.(\d+)\s*Ov', page_text)

    if not score_match:
        return None

    runs = int(score_match.group(1))
    wickets = int(score_match.group(2))

    over = 0
    ball = 0

    if over_match:
        over = int(over_match.group(1))
        ball = int(over_match.group(2))

    return runs, wickets, over, ball



# ---------------------------------------
# COMMENTARY PARSER
# ---------------------------------------

def parse_commentary(page):

    try:
        comment = page.locator("div[class*='commentary']").first.inner_text()
        return comment.lower()
    except:
        return ""


# ---------------------------------------
# EVENT DETECTION
# ---------------------------------------

def detect_event(runs, wickets, over, ball, commentary):

    global last_score, last_wickets, last_over, last_ball
    global last_commentary, free_hit_active

    if last_score is None:
        last_score = runs
        last_wickets = wickets
        last_over = over
        last_ball = ball
        last_commentary = commentary
        return "NONE"

    run_diff = runs - last_score
    new_ball = (over != last_over) or (ball != last_ball)

    event = "NONE"

    # ---------------------------------------
    # WICKET
    # ---------------------------------------

    if wickets > last_wickets:
        event = "WICKET"

    # ---------------------------------------
    # OVER COMPLETE
    # ---------------------------------------

    elif over > last_over:
        event = "OVER_COMPLETE"

    # ---------------------------------------
    # BALL EVENTS
    # ---------------------------------------

    elif new_ball:

        if "wide" in commentary:
            event = "WIDE"

        elif "no ball" in commentary:
            event = "NO_BALL"
            free_hit_active = True

        elif "bye" in commentary:
            event = "BYE"

        elif "leg bye" in commentary:
            event = "LEG_BYE"

        elif "free hit" in commentary:
            event = "FREE_HIT"

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

        elif run_diff == 6:
            event = "SIX"

        elif run_diff > 0:
            event = "RUNS"

    # ---------------------------------------
    # FREE HIT LOGIC
    # ---------------------------------------

    if free_hit_active and event not in ["NO_BALL", "FREE_HIT"]:
        event = "FREE_HIT_" + event
        free_hit_active = False

    # ---------------------------------------
    # UPDATE STATE
    # ---------------------------------------

    last_score = runs
    last_wickets = wickets
    last_over = over
    last_ball = ball
    last_commentary = commentary

    return event


# ---------------------------------------
# MATCH RESULT DETECTION
# ---------------------------------------

def detect_match_result(page_text):

    text = page_text.lower()

    if "won by" in text:

        result = re.search(r'([a-z\s]+)\s+won by\s+([a-z0-9\s]+)', text)

        if result:
            team = result.group(1).strip()
            margin = result.group(2).strip()

            return {
                "winner": team,
                "margin": margin
            }

    return None


# ---------------------------------------
# WRITE JSON
# ---------------------------------------

def write_json(score, wickets, over, ball, event, result):

    data = {
        "score": score,
        "wickets": wickets,
        "over": over,
        "ball": ball,
        "event": event,
        "winner": None,
        "margin": None
    }

    if result:
        data["winner"] = result["winner"]
        data["margin"] = result["margin"]
        data["event"] = "MATCH_RESULT"

    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=4)

    print("Updated JSON:", data)


# ---------------------------------------
# MAIN LOOP
# ---------------------------------------

def main():

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        print("Opening match page...")

        page.goto(CREX_URL)

        while True:

            try:

                page.reload()

                page_text = page.inner_text("body")

                score_data = parse_score(page_text)

                if not score_data:
                    time.sleep(REFRESH_INTERVAL)
                    continue

                runs, wickets, over, ball = score_data

                commentary = parse_commentary(page)

                event = detect_event(runs, wickets, over, ball, commentary)

                result = detect_match_result(page_text)

                write_json(runs, wickets, over, ball, event, result)

            except Exception as e:
                print("Error:", e)

            time.sleep(REFRESH_INTERVAL)


# ---------------------------------------
# START
# ---------------------------------------

if __name__ == "__main__":
    main()