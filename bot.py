import os
import requests
from flask import Flask, request

# 🔐 PASTE YOUR NEW BOT TOKEN BELOW (ONE LINE ONLY)
BOT_TOKEN = "import os
import requests
from flask import Flask, request

# 🔐 PASTE YOUR NEW BOT TOKEN BELOW (ONE LINE ONLY)
BOT_TOKEN = "8504453160: AAH3Xy06U970-TnME9X1eHuLEW7h5j9iuro"

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    message = data.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "")

    if text == "/start":
        send_message(chat_id, "Hello 👋 I am AstroGuide.")

    return "ok"


def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)"

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    message = data.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text", "")

    if text == "/start":
        send_message(chat_id, "Hello 👋 I am AstroGuide.")

    return "ok"


def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
