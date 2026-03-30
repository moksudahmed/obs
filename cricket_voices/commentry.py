import random

# -----------------------------
# Number → Bangla Words
# -----------------------------
BN_NUMBERS = {
    0: "শূন্য", 1: "এক", 2: "দুই", 3: "তিন", 4: "চার",
    5: "পাঁচ", 6: "ছয়", 7: "সাত", 8: "আট", 9: "নয়",
    10: "দশ", 11: "এগারো", 12: "বারো", 13: "তেরো",
    14: "চৌদ্দ", 15: "পনেরো", 16: "ষোল", 17: "সতেরো",
    18: "আঠারো", 19: "উনিশ", 20: "বিশ"
}

def num_to_bn(n):
    """Convert small numbers to Bangla words, fallback to string"""
    return BN_NUMBERS.get(n, str(n))


# -----------------------------
# MAIN FUNCTION
# -----------------------------
import random

COMMENTARY = {
    "SIX": [
        "ওহ, বলটি বাউন্ডারির বাইর! ছক্কা! ব্যাটসম্যান দারুণ timing দেখিয়েছে।",
        "দর্শকরা উচ্ছ্বাসে, এটা ছিল একটি বিশাল ছয়! ব্যাটিং অনবদ্য।",
        "ধাতব্য শট! বলটি লং অফের বাইর চলে গেল। ছক্কা!",
        "একেবারেই চমকপ্রদ! ব্যাটসম্যান বলটিকে আকাশে ছুঁড়ে দিল, ছক্কা।",
        "অসাধারণ! মাঠ ভরপুর হয়ে উঠলো এই বিশাল ছক্কার জন্য।"
    ],
    "FOUR": [
        "ফিল্ডাররা চেষ্টা করলেও ব্যর্থ, চার রান! ব্যাটসম্যান চমৎকার শট খেলেছে।",
        "বল পয়সার মতো বাউন্ডারিতে গিয়ে থামলো, চার রান!",
        "দারুণ timing! ব্যাট থেকে বল চলে গেল বাউন্ডারিতে, চার।",
        "মধ্যম মাঠের ফিল্ডাররা বল ধরতে পারলেন না, চার রান!",
        "ফিল্ডারদের ছুটে দৌড়ানোই যথেষ্ট হয়নি, বল বাউন্ডারি ছুঁলো।"
    ],
    "DOUBLE": [
        "দুটি রান! ব্যাটসম্যান চতুরভাবে বল চালাল এবং দু'পদে নিরাপদে পৌঁছালো।",
        "দারুণ জগিং, ব্যাটসম্যান স্কোর যোগ করল দুটি রান।",
        "ফিল্ডারদের চেষ্টার মাঝেও দু'টি রান নিরাপদে যোগ হলো।",
        "দুটি সুন্দর রান! ব্যাটসম্যান smart খেলেছে।",
        "দুই পা, দুই রান! ব্যাটসম্যান দ্রুত রান তুলেছে।"
    ],
    "SINGLE": [
        "একটি রান যোগ হলো। ব্যাটসম্যান সতর্কভাবে বল খেলেছে।",
        "চুপচাপ একটি রান! ফিল্ডাররা বলটি দ্রুত ফেরত দিল।",
        "একটি নিরাপদ রান। ব্যাটসম্যান দায়িত্বশীল খেলছে।",
        "একটি সহজ রান। ফিল্ডারদের চেষ্টার মধ্যেও ব্যাটসম্যান এগিয়ে গেল।",
        "একটি সুন্দর শট এবং একটি রান! স্কোর বৃদ্ধি পাচ্ছে।"
    ],
    "DOT": [
        "কোনও রান হয়নি। বলটি নিয়ন্ত্রিতভাবে খেলেছে ব্যাটসম্যান।",
        "ডট বল! ব্যাটসম্যান সুযোগ নিতে পারল না।",
        "ফিল্ডাররা আনন্দিত, রান হয়নি।",
        "এই ওভারেও একটি রানের জন্য চাপ তৈরি করা হলো ব্যাটসম্যানের ওপর।",
        "ডট বল! ব্যাটসম্যানকে আরও আগ্রাসী হতে হবে।"
    ],
    "WIDE": [
        "ওহ, ওভারসের অসাবধানতা! ওয়াইড বল, এক রান যোগ হলো।",
        "উইকেটের বিপদ বাড়লো না, ওয়াইড বল! একটি রান স্কোরে।",
        "ফিল্ডারদের আরাম, কিন্তু ওয়াইড বল দিয়ে রান এসেছে।",
        "ওভার নিয়ন্ত্রণ ব্যর্থ, ওয়াইড! স্কোরে যোগ হলো।",
        "বোলারের অসাবধানতা! ওয়াইড বল, রান বাড়ছে।"
    ],
    "NO_BALL": [
        "নো-বল! ব্যাটসম্যানকে এটি free-shot হিসেবে নিতে হবে।",
        "ওহ, বোলার ভুলে গেল, নো-বল! ব্যাটসম্যান সুবিধা নিতে পারে।",
        "নো-বল! অতিরিক্ত একটি রান যোগ হলো।",
        "এই ওভারে অসুবিধা, নো-বল! ব্যাটসম্যান অপেক্ষা করছে বড় শটের জন্য।",
        "নো-বল ঘোষণা হলো, ব্যাটসম্যান সুবিধা নিচ্ছে।"
    ]
}


def generate_event_commentary(events):
    """
    Generate rich, natural Bangla commentary for a given list of cricket events
    events: list of strings (SIX, FOUR, DOUBLE, SINGLE, DOT, WIDE, NO_BALL)
    """
    parts = []

    # Primary scoring events (only one of these per ball)
    if "SIX" in events:
        parts.append(random.choice(COMMENTARY["SIX"]))
    elif "FOUR" in events:
        parts.append(random.choice(COMMENTARY["FOUR"]))
    elif "DOUBLE" in events:
        parts.append(random.choice(COMMENTARY["DOUBLE"]))
    elif "SINGLE" in events:
        parts.append(random.choice(COMMENTARY["SINGLE"]))
    elif "DOT" in events:
        parts.append(random.choice(COMMENTARY["DOT"]))

    # Extras can be combined with scoring
    if "WIDE" in events:
        parts.append(random.choice(COMMENTARY["WIDE"]))

    if "NO_BALL" in events:
        parts.append(random.choice(COMMENTARY["NO_BALL"]))

    # Combine all parts into one natural paragraph
    commentary_text = " ".join(parts)
    return commentary_text
    
    
def generate_wicket_commentary2(runs, wickets, over, batsman=None):
    """
    Smart Bangla wicket commentary
    - Avoids symbols like '/'
    - Converts numbers to words
    - More natural speech flow
    """

    runs_bn = num_to_bn(runs)
    wickets_bn = num_to_bn(wickets)
    over_bn = str(over)  # keep decimal natural (TTS reads better)

    name_part = f"{batsman} ফিরে যাচ্ছেন। " if batsman else ""

    # 🎯 Normal commentary
    templates = [
        f"আউট! {name_part}দলের রান এখন {runs_bn}, উইকেট {wickets_bn}টি, {over_bn} ওভারে বড় ধাক্কা।",
        f"উইকেট পড়ে গেছে! {name_part}{over_bn} ওভারে দল করেছে {runs_bn} রান, হারিয়েছে {wickets_bn} উইকেট।",
        f"এবং আউট! {name_part}স্কোর এখন {runs_bn} রান, {wickets_bn} উইকেট, ম্যাচে নতুন মোড়।",
        f"বড় উইকেট! {name_part}{runs_bn} রানে {wickets_bn} উইকেট, চাপ বাড়ছে।",
        f"উইকেট! {name_part}এই মুহূর্তে দলের সংগ্রহ {runs_bn} রান, {wickets_bn} উইকেট।",
    ]

    # 🔥 Pressure situation
    pressure_templates = [
        f"বড় ধাক্কা! {name_part}{runs_bn} রানে {wickets_bn} উইকেট, দল কিছুটা চাপে।",
        f"গুরুত্বপূর্ণ উইকেট! {name_part}{over_bn} ওভারে {runs_bn} রান, {wickets_bn} উইকেট — ম্যাচ জমে উঠছে।",
        f"এই উইকেট ম্যাচের মোড় ঘুরিয়ে দিতে পারে! {runs_bn} রান, {wickets_bn} উইকেট।",
    ]

    # 🚨 Collapse situation
    collapse_templates = [
        f"একের পর এক উইকেট! {runs_bn} রানে {wickets_bn} উইকেট, দল বিপদে।",
        f"ব্যাটিং ধস! {runs_bn} রান, {wickets_bn} উইকেট — পরিস্থিতি কঠিন হয়ে যাচ্ছে।",
        f"চাপ বাড়ছেই! {runs_bn} রানে {wickets_bn} উইকেট পড়ে গেছে।",
    ]

    # 🎲 Smart selection logic
    if wickets >= 6:
        return random.choice(collapse_templates)

    if wickets >= 4 and random.random() > 0.5:
        return random.choice(pressure_templates)

    return random.choice(templates)
    
def generate_wicket_commentary(runs, wickets, over, batsman=None):
    """
    Long, natural Bangla wicket commentary
    - No symbols like '/'
    - Human-like flow (2–3 sentences)
    - Context-aware (normal / pressure / collapse)
    """

    runs_bn = num_to_bn(runs)
    wickets_bn = num_to_bn(wickets)
    over_bn = str(over)

    name_part = f"{batsman} ফিরে যাচ্ছেন। " if batsman else ""

    # 🎯 Normal commentary (long)
    templates = [
        f"আউট! {name_part}এটা ছিল খুবই গুরুত্বপূর্ণ একটি উইকেট। {over_bn} ওভারে দলের রান এখন {runs_bn}, আর উইকেট {wickets_bn}টি। এই মুহূর্তে ম্যাচে কিছুটা ভারসাম্য ফিরে এসেছে।",
        
        f"উইকেট পড়ে গেছে! {name_part}দারুণ একটি ব্রেকথ্রু পেয়েছে বোলিং দল। {runs_bn} রান তুলতে গিয়ে {wickets_bn} উইকেট হারিয়েছে দলটি, এবং এখন ম্যাচের গতিপথ বদলে যেতে পারে।",
        
        f"এবং আউট! {name_part}খুব গুরুত্বপূর্ণ সময় এই উইকেটের পতন। {over_bn} ওভারে স্কোর এখন {runs_bn} রান, {wickets_bn} উইকেট, ফলে ব্যাটিং দল এখন কিছুটা চাপে পড়ে গেল।",
        
        f"বড় উইকেট! {name_part}এই উইকেটটি ম্যাচে বড় প্রভাব ফেলতে পারে। দল এখন {runs_bn} রানে {wickets_bn} উইকেট হারিয়েছে, এবং এখান থেকে ঘুরে দাঁড়ানোটা সহজ হবে না।",
    ]

    # 🔥 Pressure commentary (long)
    pressure_templates = [
        f"বড় ধাক্কা! {name_part}ঠিক এই সময়েই উইকেট হারানোটা দলের জন্য সমস্যা তৈরি করতে পারে। {runs_bn} রানে {wickets_bn} উইকেট, এবং এখন ম্যাচে চাপ স্পষ্টভাবে দেখা যাচ্ছে।",
        
        f"গুরুত্বপূর্ণ উইকেট! {name_part}বোলার ঠিক সময়েই সাফল্য এনে দিলেন। {over_bn} ওভারে {runs_bn} রান, {wickets_bn} উইকেট — ব্যাটিং দল এখন চাপের মধ্যে।",
        
        f"এই উইকেট ম্যাচের মোড় ঘুরিয়ে দিতে পারে! {name_part}দল এখন {runs_bn} রানে {wickets_bn} উইকেট হারিয়েছে, এবং এখান থেকে রান তোলা সহজ হবে না।",
    ]

    # 🚨 Collapse commentary (long)
    collapse_templates = [
        f"একের পর এক উইকেট! {name_part}দল পুরোপুরি চাপে পড়ে গেছে। {runs_bn} রানে {wickets_bn} উইকেট, এবং ব্যাটিং লাইনআপ এখন ভেঙে পড়ার মুখে।",
        
        f"ব্যাটিং ধস! {name_part}এই উইকেটের পর পরিস্থিতি আরও কঠিন হয়ে গেল। {runs_bn} রান, {wickets_bn} উইকেট — এখন ম্যাচ পুরোপুরি প্রতিপক্ষের নিয়ন্ত্রণে চলে যাচ্ছে।",
        
        f"চাপ বাড়ছেই! {name_part}দল এখন দিশেহারা অবস্থায়। {runs_bn} রানে {wickets_bn} উইকেট পড়ে গেছে, এবং এখান থেকে ঘুরে দাঁড়ানো বেশ কঠিন।",
    ]

    # 🎲 Smart logic
    if wickets >= 6:
        return random.choice(collapse_templates)

    if wickets >= 4 and random.random() > 0.5:
        return random.choice(pressure_templates)

    return random.choice(templates)
# ---------------------------------------

def generate_winning_commentary(team, margin, win_type):
    """
    Advanced natural Bangla winning commentary
    - More expressive & emotional
    - Broadcast-style flow
    - Context-aware variations
    """

    if not team:
        return None

    # Normalize win type
    type_bn = "উইকেটে" if win_type == "wickets" else "রানে"

    # 🎯 Standard balanced win
    templates = [
        f"ম্যাচ শেষ, এবং জয় পেয়েছে {team}! {margin} {type_bn} দুর্দান্ত পারফরম্যান্সে তারা ম্যাচটি নিজেদের করে নিয়েছে। পুরো ম্যাচ জুড়েই ছিল নিয়ন্ত্রণ, এবং শেষ পর্যন্ত সেই ধারাবাহিকতাই এনে দিল এই জয়।",

        f"খেলা শেষ! {team} {margin} {type_bn} একটি দারুণ জয় তুলে নিল। শুরু থেকে শেষ পর্যন্ত পরিকল্পিত ক্রিকেট খেলেছে তারা, এবং প্রতিপক্ষকে খুব একটা সুযোগ দেয়নি ঘুরে দাঁড়ানোর।",

        f"জয় {team}-এর! {margin} {type_bn} তারা আজকের ম্যাচে অসাধারণ পারফরম্যান্স দেখিয়েছে। ব্যাটিং, বোলিং—সব বিভাগেই ছিল চমৎকার সমন্বয়।",

        f"এবং শেষ পর্যন্ত {team} জিতে গেল! {margin} {type_bn} এই জয় তাদের আত্মবিশ্বাস আরও বাড়াবে। পুরো ম্যাচে তারা ছিল অনেক বেশি সংগঠিত ও আত্মবিশ্বাসী।",
    ]

    # 🔥 Dominating performance
    dominant_templates = [
        f"একতরফা লড়াই বলা যায়! {team} {margin} {type_bn} বিশাল জয় তুলে নিয়েছে। শুরু থেকেই ম্যাচের নিয়ন্ত্রণ ছিল তাদের হাতে, এবং প্রতিপক্ষকে একেবারেই খেলায় ফিরতে দেয়নি।",

        f"সম্পূর্ণ আধিপত্য {team}-এর! {margin} {type_bn} এই বড় জয় প্রমাণ করে আজ তারা কতটা শক্তিশালী পারফরম্যান্স দিয়েছে। প্রতিটি বিভাগেই ছিল শ্রেষ্ঠত্ব।",

        f"দাপুটে জয়! {team} {margin} {type_bn} ব্যবধানে ম্যাচ জিতে নিয়েছে। এমন পারফরম্যান্সে তারা প্রতিপক্ষকে পুরোপুরি চাপে ফেলে দেয় এবং ম্যাচটা একদম নিজেদের মতো করে খেলেছে।",
    ]

    # 🎉 Close thriller finish
    close_templates = [
        f"কি রোমাঞ্চকর ম্যাচ! শেষ মুহূর্ত পর্যন্ত উত্তেজনা ছিল, কিন্তু শেষ হাসি হাসলো {team}। {margin} {type_bn} এই জয় সত্যিই স্মরণীয় হয়ে থাকবে।",

        f"হৃদয় কাঁপানো লড়াইয়ের পর {team} জিতে গেল! মাত্র {margin} {type_bn} এই জয় এসেছে, এবং ম্যাচটি শেষ বল পর্যন্ত জমে ছিল।",

        f"অবিশ্বাস্য সমাপ্তি! {team} শেষ মুহূর্তে ম্যাচ ছিনিয়ে নিল {margin} {type_bn} ব্যবধানে। এমন ম্যাচ ক্রিকেটপ্রেমীদের অনেকদিন মনে থাকবে।",
    ]

    # ⚡ Chase victory (wickets win special tone)
    chase_templates = [
        f"টার্গেট তাড়া করে জয়! {team} দারুণভাবে রান তাড়া করে {margin} {type_bn} জয় তুলে নিয়েছে। ব্যাটসম্যানদের আত্মবিশ্বাসী পারফরম্যান্স ছিল চোখে পড়ার মতো।",

        f"চমৎকার রান চেজ! {team} সহজভাবেই লক্ষ্য ছুঁয়ে ফেলেছে এবং {margin} {type_bn} জয় পেয়েছে। শেষ দিকে ছিল সম্পূর্ণ নিয়ন্ত্রণ।",
    ]

    # 🎲 Smart selection logic
    if win_type == "runs" and margin >= 50:
        return random.choice(dominant_templates)

    if win_type == "wickets" and margin >= 7:
        return random.choice(dominant_templates)

    if margin <= 2:
        return random.choice(close_templates)

    if win_type == "wickets" and margin >= 4:
        return random.choice(chase_templates)

    return random.choice(templates)