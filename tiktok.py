import os
import requests

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
TIKTOK_USER = "raddevil76"

def send_no_data(reason=""):
    msg = "No data" if not reason else f"No data ({reason})"
    requests.post(WEBHOOK_URL, json={"content": msg})
    print("Wysłano:", msg)

def get_latest_video():
    try:
        api_url = f"https://www.tikwm.com/api/user/posts?unique_id={TIKTOK_USER}&count=1"
        r = requests.get(api_url, timeout=10)

        if r.status_code != 200:
            return None

        data = r.json()

        if data.get("data") is None:
            return None

        videos = data["data"].get("videos")
        if not videos:
            return None

        video = videos[0]
        video_id = video["video_id"]

        return f"https://www.tiktok.com/@{TIKTOK_USER}/video/{video_id}"

    except Exception as e:
        print("Błąd API:", e)
        return None

def main():
    video_url = get_latest_video()
    if not video_url:
        send_no_data("API")
        return

    requests.post(WEBHOOK_URL, json={"content": video_url})
    print("Wysłano link:", video_url)

if __name__ == "__main__":
    main()
