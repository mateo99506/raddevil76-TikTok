import requests
import json
import os

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
TIKTOK_USER = "raddevil76"

def get_latest_video():
    api_url = f"https://www.tiktok.com/@{TIKTOK_USER}"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(api_url, headers=headers)

    if "video" not in r.text:
        return None

    start = r.text.find("https://www.tiktok.com/@")
    end = r.text.find("?", start)
    return r.text[start:end]

def send_to_discord(video_url):
    data = {
        "content": f"🎬 Nowy film od **@{TIKTOK_USER}**!\n{video_url}"
    }
    requests.post(WEBHOOK_URL, json=data)

latest = get_latest_video()

if latest:
    cache_file = "last.txt"
    last = ""

    if os.path.exists(cache_file):
        last = open(cache_file).read().strip()

    if latest != last:
        send_to_discord(latest)
        open(cache_file, "w").write(latest)
