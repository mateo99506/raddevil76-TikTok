import requests
import json
import os
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

def get_secuid(username):
    print("🔍 Pobieram stronę TikTok…")
    url = f"https://www.tiktok.com/@{username}"
    r = requests.get(url, headers=HEADERS)

    print("📡 Status strony:", r.status_code)
    print("📄 Pierwsze 500 znaków HTML:")
    print(r.text[:500])

    match = re.search(r'<script id="SIGI_STATE"[^>]*>(.*?)</script>', r.text)
    if not match:
        print("❌ SIGI_STATE nie znaleziony.")
        return None

    try:
        sigi = json.loads(match.group(1))
        secuid = sigi["UserModule"]["users"][username]["secUid"]
        print("✅ secUid:", secuid)
        return secuid
    except Exception as e:
        print("❌ Błąd parsowania SIGI_STATE:", e)
        return None

def get_latest_video(secuid):
    print("🎬 Pobieram najnowszy film…")
    api_url = (
        "https://www.tiktok.com/api/post/item_list/"
        f"?aid=1988&count=1&secUid={secuid}"
    )

    r = requests.get(api_url, headers=HEADERS)
    print("📡 Status API:", r.status_code)
    print("📄 Pierwsze 500 znaków JSON:")
    print(r.text[:500])

    try:
        data = r.json()
        item = data["itemList"][0]

        video_id = item["id"]
        desc = item.get("desc", "")
        thumbnail = item["video"]["cover"]

        video_url = f"https://www.tiktok.com/@{TIKTOK_USER}/video/{video_id}"

        print("🎯 Najnowszy film:", video_url)
        return {
            "url": video_url,
            "desc": desc,
            "thumbnail": thumbnail,
        }

    except Exception as e:
        print("❌ Błąd parsowania JSON:", e)
        return None

def send_embed(video):
    print("📤 Wysyłam embed na Discord…")
    payload = {
        "embeds": [
            {
                "title": f"Nowy film od @{TIKTOK_USER}",
                "description": video["desc"] or "Brak opisu.",
                "url": video["url"],
                "color": 0x00FFFF,
                "image": {"url": video["thumbnail"]},
            }
        ]
    }

    r = requests.post(WEBHOOK_URL, json=payload)
    print("📡 Webhook status:", r.status_code)
    print("📄 Odpowiedź Discorda:", r.text)

def main():
    secuid = get_secuid(TIKTOK_USER)
    if not secuid:
        print("❌ secUid nie został pobrany — STOP")
        return

    latest = get_latest_video(secuid)
    if not latest:
        print("❌ Nie udało się pobrać filmu — STOP")
        return

    cache_file = "last.txt"
    last = ""

    if os.path.exists(cache_file):
        last = open(cache_file).read().strip()

    if latest["url"] != last:
        print("📢 Nowy film — wysyłam!")
        send_embed(latest)
        open(cache_file, "w").write(latest["url"])
    else:
        print("ℹ️ Brak nowych filmów.")

if __name__ == "__main__":
    main()
