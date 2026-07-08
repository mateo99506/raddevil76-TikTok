import os
import requests
import time

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

    # Fix double URL
    if "https://" in cover:
        parts = cover.split("https://")
        if len(parts) >= 2:
            cover = "https://" + parts[1]

    # If path starts with "/"
    if cover.startswith("/"):
        cover = "https://www.tikwm.com" + cover

    # If not a full URL
    if not cover.startswith("http"):
        cover = "https://www.tikwm.com" + cover

    # HEIC → JPG
    if ".heic" in cover:
        print("HEIC detected, converting to JPG:", cover)
        cover = cover.replace(".heic", ".jpg")

    return cover


# --- Fetch last TikTok videos ---
def get_latest_videos():
    try:
        api_url = f"https://www.tikwm.com/api/user/posts?unique_id={TIKTOK_USER}&count=24"
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

        result = []
        for v in videos:
            result.append({
                "id": v["video_id"],
                "title": v.get("title", "No description"),
                "cover": v.get("cover", ""),
            })

        return result

    except Exception as e:
        print("API exception:", e)
        return None


# --- Load memory (list of IDs) ---
def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                return []
            return content.split("\n")
    except:
        return []


# --- Save memory (list of IDs) ---
def save_memory(id_list):
    with open(MEMORY_FILE, "w") as f:
        f.write("\n".join(id_list))


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

    videos = get_latest_videos()
    if not videos:
        print("No video data")
        return

    latest_ids = [v["id"] for v in videos]
    memory_ids = load_memory()

    print("Memory IDs:", memory_ids)
    print("Latest IDs:", latest_ids)

    # Find new videos
    new_videos = [v for v in videos if v["id"] not in memory_ids]

    if not new_videos:
        print("No new videos found. Skipping.")
    else:
        print(f"Found {len(new_videos)} new videos.")

        for index, v in enumerate(new_videos):
            send_embed(v)

            # --- NEW: 2-second delay between messages ---
            if index < len(new_videos) - 1:
                print("Waiting 2 seconds before next send...")
                time.sleep(2)

    # Overwrite memory with the latest 9 IDs
    save_memory(latest_ids)
    print("Memory updated.")


if __name__ == "__main__":
    main()
