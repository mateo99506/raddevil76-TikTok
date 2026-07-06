import os
import requests

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
TIKTOK_USER = "raddevil76"

def send_no_data(reason=""):
    msg = "No data" if not reason else f"No data ({reason})"
    requests.post(WEBHOOK_URL, json={"content": msg})
    print("Sent:", msg)

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

        return {
            "id": video["video_id"],
            "title": video.get("title", "No description"),
            "cover": video.get("cover"),
        }

    except Exception as e:
        print("API error:", e)
        return None

def send_embed(video):
    video_url = f"https://www.tiktok.com/@{TIKTOK_USER}/video/{video['id']}"

    embed = {
        "embeds": [
            {
                "title": f"New TikTok video by @{TIKTOK_USER}",
                "description": video["title"],
                "url": video_url,
                "color": 0x00FFFF,
                "image": {"url": video["cover"]},
            }
        ]
    }

    requests.post(WEBHOOK_URL, json=embed)
    print("Embed sent:", video_url)

def main():
    video = get_latest_video()
    if not video:
        send_no_data("API")
        return

    send_embed(video)

if __name__ == "__main__":
    main()
