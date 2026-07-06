import os
import requests

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

requests.post(WEBHOOK_URL, json={"content": "Test"})
print("Test.")
