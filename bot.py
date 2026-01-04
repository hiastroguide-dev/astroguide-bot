import os
import json
import requests
from flask import Flask, request
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ASTRO_API_KEY = os.environ.get("ASTRO_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")
if not ASTRO_API_KEY:
    raise RuntimeError("ASTRO_API_KEY is not set")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
ASTRO_BASE_URL = "https://json.freeastrologyapi.com"

app = Flask(__name__)

# In-memory storage (replace with DB in production)
user_state = {}
user_data_cache = {}

# Question patterns
QUESTION_PATTERNS = {
    "career": {"keywords": ["job", "career", "work", "business", "profession"], "api": "/d10-chart-info"},
    "marriage": {"keywords": ["marriage", "spouse", "partner", "wedding", "relationship"], "api": "/navamsa-chart-info"},
    "health": {"keywords": ["health", "disease", "illness", "sick"], "api": "/d30-chart-info"},
    "timing": {"keywords": ["when", "timing", "muhurat", "today"], "api": "/abhijit-muhurat"}
}

def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)

def geocode_place(place_str):
    try:
        resp = requests.get("https://nominatim.openstreetmap.org/search", 
                          params={"q": place_str, "format": "json", "limit": 1},
                          headers={"User-Agent": "AstroBot/1.0"}, timeout=10)
        data = resp.json()
        if data: return float(data[0]["lat"]), float(data[0]["lon"])
    except: pass
    return 28.6139, 77.2090

def parse_birth_data(dob_str, time_str, place_str):
    day, month, year = map(int, dob_str.split("-"))
    if "AM" in time_str.upper() or "PM" in time_str.upper():
        time_obj = datetime.strptime(time_str.replace(" ", ""), "%I:%M%p")
        hours, minutes = time_obj.hour, time_obj.minute
    else:
        parts = time_str.split(":")
        hours, minutes = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    lat, lon = geocode_place(place_str)
    return {"year": year, "month": month, "date": day, "hours": hours, "minutes": minutes, 
            "seconds": 0, "latitude": lat, "longitude": lon, "timezone": 5.5,
            "settings": {"observation_point": "topocentric", "ayanamsha": "lahiri", "language": "en"}}

def call_astro_api(endpoint, payload):
    try:
        resp = requests.post(f"{ASTRO_BASE_URL}{endpoint}", json=payload,
                           headers={"Content-Type": "application/json", "x-api-key": ASTRO_API_KEY}, timeout=15)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def register_user_data(chat_id, dob_str, time_str, place_str):
    payload = parse_birth_data(dob_str, time_str, place_str)
    planets_data = call_astro_api("/planets/extended", payload)
    now = datetime.now()
    dasa_payload = payload.copy()
    dasa_payload["event_data"] = {"year": now.year, "month": now.month, "date": now.day,
                                   "hours": now.hour, "minutes": now.minute, "seconds": 0}
    dasa_data = call_astro_api("/vimsottari/dasa-information", dasa_payload)
    user_data_cache[chat_id] = {"birth_data": {"dob": dob_str, "time": time_str, "place": place_str, "payload": payload},
                                 "planets_data": planets_data, "dasa_data": dasa_data, "cached_at": datetime.now().isoformat()}
    return planets_data, dasa_data

def format_basic_summary(planets_data, dasa_data):
    try:
        output = planets_data.get("output", {})
        moon = output.get("Moon", {})
        ascendant = output.get("Ascendant", {})
        maha = dasa_data.get("maha_dasa", {})
        antar = dasa_data.get("antar_dasa", {})
        return (f"✅ Birth chart registered!\n\n"
                f"🌟 Nakshatra: {moon.get('nakshatra_name', 'N/A')} (Pada {moon.get('nakshatra_pada', 'N/A')})\n"
                f"🔮 Ascendant: {ascendant.get('zodiac_sign_name', 'N/A')}\n"
                f"🌙 Moon Sign: {moon.get('zodiac_sign_name', 'N/A')}\n\n"
                f"⏳ Current Dasa:\n  Maha: {maha.get('Lord', 'N/A')} (till {maha.get('end_time', 'N/A')[:10]})\n"
                f"  Antar: {antar.get('Lord', 'N/A')}\n\n"
                f"💬 Ask: career, marriage, health, timing")
    except:
        return "✅ Data registered! Ask questions now."

def classify_question(question_text):
    question_lower = question_text.lower()
    for category, config in QUESTION_PATTERNS.items():
        if any(kw in question_lower for kw in config["keywords"]):
            return category, config["api"]
    return "general", None

def answer_question(chat_id, question_text):
    if chat_id not in user_data_cache:
        return "❌ Register first with /start"
    cache = user_data_cache[chat_id]
    planets_data = cache["planets_data"]
    dasa_data = cache["dasa_data"]
    birth_payload = cache["birth_data"]["payload"]
    category, api_endpoint = classify_question(question_text)
    if api_endpoint:
        send_message(chat_id, f"🔍 Analyzing your {category}...")
        if api_endpoint in ["/d10-chart-info", "/navamsa-chart-info", "/d30-chart-info"]:
            additional_data = call_astro_api(api_endpoint, birth_payload)
        elif api_endpoint == "/abhijit-muhurat":
            today = datetime.now()
            timing_payload = {"year": today.year, "month": today.month, "date": today.day,
                            "latitude": birth_payload["latitude"], "longitude": birth_payload["longitude"], "timezone": 5.5}
            additional_data = call_astro_api(api_endpoint, timing_payload)
    output = planets_data.get("output", {})
    maha = dasa_data.get("maha_dasa", {})
    if category == "career":
        sun = output.get("Sun", {})
        return (f"📊 CAREER\n\nSun: {sun.get('zodiac_sign_name')} in House {sun.get('house_number')}\n"
                f"Current Dasa: {maha.get('Lord')}\nGood for professional growth.")
    elif category == "marriage":
        venus = output.get("Venus", {})
        return (f"💑 MARRIAGE\n\nVenus: {venus.get('zodiac_sign_name')} in House {venus.get('house_number')}\n"
                f"Current Dasa: {maha.get('Lord')}\nMarriage timing depends on transits.")
    elif category == "health":
        moon = output.get("Moon", {})
        return f"🏥 HEALTH\n\nMoon: {moon.get('zodiac_sign_name')}\nCheck 6th/8th houses for concerns."
    else:
        moon = output.get("Moon", {})
        return (f"✨ GENERAL\n\nNakshatra: {moon.get('nakshatra_name')}\n"
                f"Moon: {moon.get('zodiac_sign_name')}\nCurrent Dasa: {maha.get('Lord')}")

@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "GET": return "OK", 200
    data = request.get_json(silent=True) or {}
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = (message.get("text") or "").strip()
    if not chat_id or not text: return "ok", 200
    
    if text == "/start":
        user_state[chat_id] = {"step": "ask_name", "data": {}}
        send_message(chat_id, "Hi! What's your name?")
        return "ok", 200
    
    if chat_id not in user_state:
        if chat_id in user_data_cache:
            answer = answer_question(chat_id, text)
            send_message(chat_id, answer)
        else:
            send_message(chat_id, "/start to register")
        return "ok", 200
    
    state = user_state[chat_id]
    step = state.get("step")
    data_store = state.get("data", {})
    
    if step == "ask_name":
        data_store["name"] = text
        state["step"] = "ask_dob"
        send_message(chat_id, "DOB (DD-MM-YYYY)?")
    elif step == "ask_dob":
        data_store["dob"] = text
        state["step"] = "ask_time"
        send_message(chat_id, "Time of birth (HH:MM)?")
    elif step == "ask_time":
        data_store["time_of_birth"] = text
        state["step"] = "ask_place"
        send_message(chat_id, "Place of birth (City, Country)?")
    elif step == "ask_place":
        data_store["place_of_birth"] = text
        send_message(chat_id, "⏳ Fetching data...")
        planets_data, dasa_data = register_user_data(chat_id, data_store["dob"], data_store["time_of_birth"], data_store["place_of_birth"])
        summary = format_basic_summary(planets_data, dasa_data)
        send_message(chat_id, summary)
        del user_state[chat_id]
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
