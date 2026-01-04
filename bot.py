import os
import requests
from flask import Flask, request

# Read token securely from Render environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
app = Flask(__name__)

# In-memory storage for user conversations (per chat_id)
user_data = {}

# Conversation states
STATE_START = "start"
STATE_NAME = "name"
STATE_DOB = "dob"
STATE_TIME = "time"
STATE_PLACE = "place"
STATE_QUESTION = "question"
STATE_PARTNER_NAME = "partner_name"
STATE_PARTNER_DOB = "partner_dob"
STATE_PARTNER_TIME = "partner_time"
STATE_PARTNER_PLACE = "partner_place"
STATE_COMPLETE = "complete"

@app.route("/", methods=["GET", "POST"])
def webhook():
    # Render may send GET requests (health check)
    if request.method == "GET":
        return "OK", 200
    
    # Log incoming webhook data
    print(f"Received webhook: {request.method}")
    
    data = request.get_json(silent=True) or {}
    print(f"Data: {data}")
    
    message = data.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "").strip()
    
    print(f"Chat ID: {chat_id}, Text: {text}")
    
    if chat_id:
        handle_message(chat_id, text)
    
    # Always return 200 OK to Telegram
    return "ok", 200

def handle_message(chat_id, text):
    """Handle incoming messages and manage conversation state"""
    
    # Initialize user data if not exists
    if chat_id not in user_data:
        user_data[chat_id] = {
            "state": STATE_START,
            "data": {}
        }
    
    current_state = user_data[chat_id]["state"]
    
    # Handle /start command
    if text.lower() == "/start":
        user_data[chat_id] = {
            "state": STATE_NAME,
            "data": {}
        }
        send_message(chat_id, "Hello 👋 Welcome to AstroGuide!\n\nI'll help you with your astrological queries. Let's start by collecting some information.\n\nWhat's your name?")
        return
    
    # Handle conversation flow based on state
    if current_state == STATE_NAME:
        user_data[chat_id]["data"]["name"] = text
        user_data[chat_id]["state"] = STATE_DOB
        send_message(chat_id, f"Nice to meet you, {text}! 🌟\n\nWhat's your date of birth? (Please provide in DD/MM/YYYY format)")
    
    elif current_state == STATE_DOB:
        user_data[chat_id]["data"]["dob"] = text
        user_data[chat_id]["state"] = STATE_TIME
        send_message(chat_id, "Great! 🕒\n\nWhat's your time of birth? (Please provide in HH:MM format, e.g., 14:30)")
    
    elif current_state == STATE_TIME:
        user_data[chat_id]["data"]["time_of_birth"] = text
        user_data[chat_id]["state"] = STATE_PLACE
        send_message(chat_id, "Perfect! 🌍\n\nWhat's your place of birth? (City, Country)")
    
    elif current_state == STATE_PLACE:
        user_data[chat_id]["data"]["place_of_birth"] = text
        user_data[chat_id]["state"] = STATE_QUESTION
        send_message(chat_id, "Excellent! 💫\n\nWhat type of question do you have?\n\n1. Career\n2. Relationship\n3. Health\n4. Finance\n5. General\n\nPlease type the number or name of the category.")
    
    elif current_state == STATE_QUESTION:
        question_type = text.lower()
        user_data[chat_id]["data"]["question_type"] = text
        
        # Check if it's a relationship question
        if "2" in text or "relationship" in question_type:
            user_data[chat_id]["state"] = STATE_PARTNER_NAME
            send_message(chat_id, "💑 You've selected Relationship.\n\nI'll need your partner's details too.\n\nWhat's your partner's name?")
        else:
            user_data[chat_id]["state"] = STATE_COMPLETE
            show_summary(chat_id)
    
    elif current_state == STATE_PARTNER_NAME:
        user_data[chat_id]["data"]["partner_name"] = text
        user_data[chat_id]["state"] = STATE_PARTNER_DOB
        send_message(chat_id, f"What's {text}'s date of birth? (DD/MM/YYYY format)")
    
    elif current_state == STATE_PARTNER_DOB:
        user_data[chat_id]["data"]["partner_dob"] = text
        user_data[chat_id]["state"] = STATE_PARTNER_TIME
        send_message(chat_id, "What's your partner's time of birth? (HH:MM format)")
    
    elif current_state == STATE_PARTNER_TIME:
        user_data[chat_id]["data"]["partner_time_of_birth"] = text
        user_data[chat_id]["state"] = STATE_PARTNER_PLACE
        send_message(chat_id, "What's your partner's place of birth? (City, Country)")
    
    elif current_state == STATE_PARTNER_PLACE:
        user_data[chat_id]["data"]["partner_place_of_birth"] = text
        user_data[chat_id]["state"] = STATE_COMPLETE
        show_summary(chat_id)
    
    elif current_state == STATE_COMPLETE:
        send_message(chat_id, "Thanks! Your information is already recorded. Type /start to begin a new consultation.")

def show_summary(chat_id):
    """Display collected information summary"""
    data = user_data[chat_id]["data"]
    
    summary = f"✨ **Information Collected** ✨\n\n"
    summary += f"👤 **Your Details:**\n"
    summary += f"Name: {data.get('name')}\n"
    summary += f"DOB: {data.get('dob')}\n"
    summary += f"Time: {data.get('time_of_birth')}\n"
    summary += f"Place: {data.get('place_of_birth')}\n"
    summary += f"Question Type: {data.get('question_type')}\n"
    
    if "partner_name" in data:
        summary += f"\n💑 **Partner's Details:**\n"
        summary += f"Name: {data.get('partner_name')}\n"
        summary += f"DOB: {data.get('partner_dob')}\n"
        summary += f"Time: {data.get('partner_time_of_birth')}\n"
        summary += f"Place: {data.get('partner_place_of_birth')}\n"
    
    summary += f"\n✅ All information has been saved!\n"
    summary += f"\n📝 In the next phase, I'll analyze your data and provide insights.\n\n"
    summary += f"Type /start to begin a new consultation."
    
    send_message(chat_id, summary)

def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    response = requests.post(url, json=payload, timeout=10)
    print(f"Send message response: {response.status_code}")
    return response

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
