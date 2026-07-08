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


# --- Clean TikTok cover URL (fixes TikWM double-URL bug) ---
def clean_cover_url(cover):
    if not cover:
        return None

    # If TikWM returns a double URL like:
    # "https://www.tikwm.comhttps://p16-common-sign.tiktokcdn-eu.com/..."
    if "https://" in cover:
        parts = cover.split("https://")
        if len(parts) >= 2:
            cover = "https://" + parts[1]

    # If TikWM returns a path starting with "/"
    if cover.startswith("/"):
        cover = "https://www.tikwm.com" + cover

    # If TikWM returns a normal full URL
    if cover.startswith("http"):
        pass
    else:
        cover = "https://www.tikwm.com" + cover

    # --- NEW: Automatic HEIC → JPG conversion ---
    if ".heic" in cover:
        print("HEIC detected, converting to JPG:", cover)
        cover = cover.replace(".heic", ".jpg")

    return cover


# --- Fetch latest TikTok video ---
def get_latest_video():
    try:
        api_url = f"https://www.tikwm.com/api/user/posts?unique_id={TIKTOK_USER}&count=1"
        r = requests.get(api_url, timeout=10)

        if r.status_code != 200:
            print("API error:", r.status_code)
            return None

        data = r.json()
        if data.get("data") is None:
            print("API returned no data")
            return None

        videos = data["data"].get("videos")
        if not videos:
            print("No videos found")
            return None

        video = videos[0]

        return {
            "id": video["video_id"],
            "title": video.get("title", "No description"),
            "cover": video.get("cover", ""),
        }

    except Exception as e:
        print("API exception:", e)
        return None


# --- Load memory ---
def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return f.read().strip()
    except:
        return None


# --- Save memory ---
def save_memory(video_id):
    with open(MEMORY_FILE, "w") as f:
        f.write(video_id)


# --- Send Discord embed ---
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
                "image": {"url": final_cover} if final_cover else {},
            }
        ]
    }

    print("Sending embed:", embed)

    resp = requests.post(WEBHOOK_URL, json=embed)
    print("Discord status:", resp.status_code)
    print("Discord response:", resp.text)


# --- Main ---
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
