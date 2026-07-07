import os
import requests

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
TIKTOK_USER = "raddevil76"
MEMORY_FILE = "memory.txt"

# --- Ensure memory file exists ---
def ensure_memory_file():
    if not os.path.exists(MEMORY_FILE):
        open(MEMORY_FILE, "w").close()
        print("Created empty memory.txt")
    else:
        print("memory.txt already exists")

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

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return f.read().strip()
    except:
        return None

def save_memory(video_id):
    with open(MEMORY_FILE, "w") as f:
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
    ensure_memory_file()

    video = get_latest_video()
    if not video:
        print("No video data")
        return

    last_id = load_memory()

    if last_id == video["id"]:
        print("Video already sent. Skipping.")
        return

    send_embed(video)
    save_memory(video["id"])

if __name__ == "__main__":
    main()
