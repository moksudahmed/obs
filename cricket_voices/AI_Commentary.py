import requests
import re
import time

# -----------------------------------------
# CONFIGURATION
# -----------------------------------------
CREX_URL = "https://crex.com/scoreboard/10R2/2F2/5th-Match/1EL/1EK/akk-vs-lgt-5th-match-tillo-t20-cup-2026/live"

SCORE_FILE = "C:/cricket_voices/score.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

last_runs = 0
last_wickets = 0
last_over = 0


# -----------------------------------------
# FETCH SCORE
# -----------------------------------------
def fetch_score():

    try:
        r = requests.get(CREX_URL, headers=HEADERS, timeout=10)

        html = r.text

        score_match = re.search(r'(\d+)\s*-\s*(\d+)', html)
        over_match = re.search(r'(\d+\.\d+)\s*Ov', html)

        if score_match:

            runs = int(score_match.group(1))
            wickets = int(score_match.group(2))

            overs = 0
            if over_match:
                overs = float(over_match.group(1))

            return runs, wickets, overs

    except Exception as e:
        print("Fetch error:", e)

    return None


# -----------------------------------------
# WRITE EVENT
# -----------------------------------------
def write_event(event):

    with open(SCORE_FILE, "w") as f:
        f.write(event)

    print("EVENT:", event)


# -----------------------------------------
# DETECT EVENTS
# -----------------------------------------
def detect_event(runs, wickets, overs):

    global last_runs, last_wickets, last_over

    # run difference
    run_diff = runs - last_runs

    if run_diff == 1:
        write_event("RUN_1")

    elif run_diff == 2:
        write_event("RUN_2")

    elif run_diff == 3:
        write_event("RUN_3")

    elif run_diff == 4:
        write_event("FOUR")

    elif run_diff == 6:
        write_event("SIX")

    # wicket
    if wickets > last_wickets:
        write_event("WICKET")

    # over complete
    if int(overs) > int(last_over):
        write_event("OVER_COMPLETE")

    last_runs = runs
    last_wickets = wickets
    last_over = overs


# -----------------------------------------
# MAIN LOOP
# -----------------------------------------
def main():

    while True:

        data = fetch_score()

        if data:
            runs, wickets, overs = data
            detect_event(runs, wickets, overs)

        time.sleep(3)


if __name__ == "__main__":
    main()