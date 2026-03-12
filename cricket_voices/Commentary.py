from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

URL = "https://crex.com/scoreboard/TUU/1S2/Only-Test/16/1I/aus-w-vs-ind-w-only-test-india-women-tour-of-australia-2026/live"

# Setup headless chrome
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")

driver = webdriver.Chrome(options=chrome_options)

driver.get(URL)

# wait for page to load
time.sleep(5)

commentary_data = []

# find commentary blocks
commentary_blocks = driver.find_elements(By.CSS_SELECTOR, "div.commentary-item")

for block in commentary_blocks:
    try:
        ball = block.find_element(By.CSS_SELECTOR, ".over").text
    except:
        ball = ""

    try:
        run = block.find_element(By.CSS_SELECTOR, ".run").text
    except:
        run = ""

    try:
        text = block.find_element(By.CSS_SELECTOR, ".description").text
    except:
        text = ""

    commentary_data.append({
        "ball": ball,
        "run": run,
        "text": text
    })

driver.quit()

for c in commentary_data:
    print(f"{c['ball']} | {c['run']} | {c['text']}")