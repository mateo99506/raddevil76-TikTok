import os
import requests

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

print("Using webhook:", WEBHOOK_URL)

payload = {
    "content": "🔧 Test webhooka — jeśli widzisz tę wiadomość, wszystko działa!"
}

try:
    response = requests.post(WEBHOOK_URL, json=payload)
    print("Status code:", response.status_code)
    print("Response text:", response.text)
except Exception as e:
    print("Error:", e)
