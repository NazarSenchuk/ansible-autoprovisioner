import requests

def send_telegram_notification(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown" 
    }
    response = requests.post(url, data=payload)
    return response.json()

if __name__ == "__main__":
    send_telegram_notification(BOT_TOKEN, CHAT_ID, MESSAGE)
    print("Notification sent!")