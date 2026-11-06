import os
import requests


def notify(msg):
    """Telegram alert if configured, always prints."""
    print("[notify]", msg)
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat:
        try:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          data={"chat_id": chat, "text": f"Tarot bot: {msg}"}, timeout=20)
        except requests.RequestException:
            pass
