import os
import requests

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
SECUID = os.getenv("TIKTOK_SECUID")
TIKTOK_USER = "raddevil76"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

def send_no_data(reason=""):
    msg = "No data" if not reason else f"No data ({reason})"
    requests.post(WEBHOOK_URL, json={"content": msg})

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

    except:
        return None

def main():
    if not SECUID:
        send_no_data("missing secUid")
        return

    video_url = get_latest_video(SECUID)
    if not video_url:
        send_no_data("API")
        return

    requests.post(WEBHOOK_URL, json={"content": video_url})

if __name__ == "__main__":
    main()
