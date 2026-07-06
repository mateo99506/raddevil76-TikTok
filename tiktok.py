import os
import requests
import json
import re

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
TIKTOK_USER = "raddevil76"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.tiktok.com/",
    "Accept-Language": "en-US,en;q=0.9",
}

def send_no_data(reason=""):
    msg = "No data" if not reason else f"No data ({reason})"
    requests.post(WEBHOOK_URL, json={"content": msg})
    print("Wysłano:", msg)

def get_secuid(username):
    try:
        r = requests.get(
            f"https://www.tiktok.com/@{username}",
            headers=HEADERS,
            timeout=10
        )

        if r.status_code != 200:
            return None

        match = re.search(r'<script id="SIGI_STATE"[^>]*>(.*?)</script>', r.text)
        if not match:
            return None

        sigi = json.loads(match.group(1))
        return sigi["UserModule"]["users"][username]["secUid"]

    except Exception as e:
        print("Błąd secUid:", e)
        return None

def get_latest_video(secuid):
    try:
        api_url = (
            "https://www.tiktok.com/api/post/item_list/"
            f"?aid=1988&count=1&secUid={secuid}"
        )

        r = requests.get(api_url, headers=HEADERS, timeout=10)

        if r.status_code != 200:
            return None

        data = r.json()

        if "itemList" not in data or not data["itemList"]:
            return None

        item = data["itemList"][0]
        video_id = item["id"]

        return f"https://www.tiktok.com/@{TIKTOK_USER}/video/{video_id}"

    except Exception as e:
        print("Błąd API:", e)
        return None

def main():
    secuid = get_secuid(TIKTOK_USER)
    if not secuid:
        send_no_data("secUid")
        return

    video_url = get_latest_video(secuid)
    if not video_url:
        send_no_data("API")
        return

    requests.post(WEBHOOK_URL, json={"content": video_url})
    print("Wysłano link:", video_url)

if __name__ == "__main__":
    main()
