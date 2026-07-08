import os
import requests
from PIL import Image
from io import BytesIO

TIKTOK_USER = "raddevil76"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
MEMORY_FILE = "memory.txt"


# ------------------------------------------------------------
# Load last saved TikTok video ID from memory.txt
# Used to detect whether a new video has appeared.
# ------------------------------------------------------------
def load_last_video_id():
    if not os.path.exists(MEMORY_FILE):
        return None
    try:
        with open(MEMORY_FILE, "r") as f:
            return f.read().strip()
    except:
        return None


# ------------------------------------------------------------
# Save the latest TikTok video ID to memory.txt
# Ensures the bot does not repost the same video twice.
# ------------------------------------------------------------
def save_last_video_id(video_id):
    with open(MEMORY_FILE, "w") as f:
        f.write(video_id)


# ------------------------------------------------------------
# Remove query parameters from the cover URL
# TikWM sometimes adds ?x-expires=..., this cleans it.
# ------------------------------------------------------------
def clean_cover_url(url):
    if not url:
        return ""
    return url.split("?")[0]


# ------------------------------------------------------------
# Fetch the latest TikTok video using TikWM API
# Returns a dictionary with video metadata.
# ------------------------------------------------------------
def get_latest_video():
    url = f"https://www.tikwm.com/api/user/posts?unique_id={TIKTOK_USER}&count=1"
    r = requests.get(url, timeout=10)
    data = r.json()

    if data.get("code") != 0:
        print("TikWM error:", data)
        return None

    video = data["data"]["videos"][0]

    return {
        "id": video["video_id"],
        "title": video["title"],
        "cover": "https://www.tikwm.com" + video["cover"],
        "url": video["play"],
        "create_time": video["create_time"]
    }


# ------------------------------------------------------------
# Send a Discord embed with information about the new TikTok video
# Uses only the webhook URL stored in GitHub Secrets.
# ------------------------------------------------------------
def send_embed(video):
    video_url = f"https://www.tiktok.com/@{TIKTOK_USER}/video/{video['id']}"
    final_cover = clean_cover_url(video.get("cover", ""))

    embed = {
        "embeds": [
            {
                "title": f"New TikTok video by @{TIKTOK_USER}",
                "description": video["title"],
                "url": video_url,
                "color": 0x00FFFF,
                "image": {"url": final_cover} if final_cover else {}
            }
        ]
    }

    print("Sending embed:", embed)
    resp = requests.post(WEBHOOK_URL, json=embed)
    print("Discord status:", resp.status_code)
    print("Discord response:", resp.text)


# ------------------------------------------------------------
# Main logic:
# - Fetch latest video
# - Compare with memory.txt
# - If new → send embed + update memory
# ------------------------------------------------------------
def main():
    print("Checking TikTok…")

    video = get_latest_video()
    if not video:
        print("No video found.")
        return

    last_id = load_last_video_id()
    print("Last ID:", last_id)
    print("Current ID:", video["id"])

    if last_id == video["id"]:
        print("No new video.")
        return

    print("New video detected!")
    send_embed(video)
    save_last_video_id(video["id"])
    print("Done.")


if __name__ == "__main__":
    main()
