from playwright.sync_api import sync_playwright
import re
import json
import time

CREX_URL = "https://crex.com/scoreboard/10U4/2F9/1st-T20/1F7/IM/bot-vs-les-1st-t20-lesotho-tour-of-botswana-2026/live"

OUTPUT_FILE = "C:/cricket_voices/score.json"


def parse_score(page_text):

    # Find patterns like 116-38.2 or 103-27.4
    score_match = re.search(r'(\d+)-(\d)(\d+)\.(\d)', page_text)
    #print(page_text)
    if score_match:
        runs = int(score_match.group(1))
        wickets = int(score_match.group(2))
        over = int(score_match.group(3))
        ball = int(score_match.group(4))

        return {
            "score": runs,
            "wickets": wickets,
            "over": over,
            "ball": ball
        }

    # Fallback if normal format exists
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

    return {
        "score": runs,
        "wickets": wickets,
        "over": over,
        "ball": ball
    }

def write_json(data):

    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=4)

    print("Updated JSON:", data)


def main():

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(CREX_URL)

        while True:

            try:

                page.reload()

                text = page.inner_text("body")

                data = parse_score(text)

                if data:
                    write_json(data)

            except Exception as e:
                print("Error:", e)

            time.sleep(3)


if __name__ == "__main__":
    main()