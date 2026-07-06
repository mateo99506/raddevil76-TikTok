import os
import requests

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
TIKTOK_USER = "raddevil76"
CACHE_FILE = "last.txt"

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
            "cover": "https://www.tikwm.com" + video.get("cover", ""),
        }

    except Exception as e:
        print("API error:", e)
        return None

def already_posted(video_id):
    if not os.path.exists(CACHE_FILE):
        return False

    last = open(CACHE_FILE).read().strip()
    return last == video_id

def update_cache(video_id):
    with open(CACHE_FILE, "w") as f:
        f.write(video_id)

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

    if already_posted(video["id"]):
        print("Video already posted. Skipping.")
        return

    send_embed(video)
    update_cache(video["id"])

if __name__ == "__main__":
    main()
