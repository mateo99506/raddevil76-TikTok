import requests
import json
import os

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
TIKTOK_USER = "raddevil76"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def get_secuid(username):
    """Pobiera secUid użytkownika z JSON osadzonego w stronie."""
    url = f"https://www.tiktok.com/@{username}"
    r = requests.get(url, headers=HEADERS)

    if r.status_code != 200:
        return None

    # Szukamy JSON-a z secUid
    marker = '"secUid":"'
    start = r.text.find(marker)
    if start == -1:
        return None

    start += len(marker)
    end = r.text.find('"', start)
    secuid = r.text[start:end]

    return secuid


def get_latest_video(secuid):
    """Pobiera najnowszy film z API TikToka."""
    api_url = (
        "https://www.tiktok.com/api/post/item_list/"
        f"?aid=1988&count=1&secUid={secuid}"
    )

    r = requests.get(api_url, headers=HEADERS)
    if r.status_code != 200:
        return None

    data = r.json()

    try:
        item = data["itemList"][0]
        video_id = item["id"]
        video_url = f"https://www.tiktok.com/@{TIKTOK_USER}/video/{video_id}"
        return video_url
    except:
        return None


def send_to_discord(video_url):
    payload = {
        "content": f"🎬 Nowy film od **@{TIKTOK_USER}**!\n{video_url}"
    }
    requests.post(WEBHOOK_URL, json=payload)


def main():
    secuid = get_secuid(TIKTOK_USER)
    if not secuid:
        print("❌ Nie udało się pobrać secUid.")
        return

    latest = get_latest_video(secuid)
    if not latest:
        print("❌ Nie udało się pobrać najnowszego filmu.")
        return

    cache_file = "last.txt"
    last = ""

    if os.path.exists(cache_file):
        last = open(cache_file).read().strip()

    if latest != last:
        print("📢 Wysyłam nowy film na Discord:", latest)
        send_to_discord(latest)
        open(cache_file, "w").write(latest)
    else:
        print("ℹ️ Brak nowych filmów.")


if __name__ == "__main__":
    main()
