import os
import json
import requests
from datetime import datetime
import subprocess
from io import BytesIO
import time

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

MEMORY_FILE = "memory.txt"
API_DUMP_FILE = "api_dump.txt"

# Global
TIKTOK_USER = "unknown"


# --- Ensure memory file exists ---
def ensure_memory_file():
    if not os.path.exists(MEMORY_FILE):
        open(MEMORY_FILE, "w").close()
        print("Created empty memory.txt")
    else:
        print("memory.txt already exists")


# --- Load memory (list of IDs) ---
def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            data = f.read().strip()
            if not data:
                return []
            return data.split(",")
    except:
        return []


# --- Save memory (list of IDs) ---
def save_memory(ids):
    with open(MEMORY_FILE, "w") as f:
        f.write(",".join(ids))


# --- Read API dump instead of requesting TikWM ---
def get_latest_videos():
    global TIKTOK_USER

    if not os.path.exists(API_DUMP_FILE):
        print("ERROR: api_dump.txt not found!")
        return None

    try:
        with open(API_DUMP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("JSON read error:", e)
        return None

    if data.get("code") != 0:
        print("Invalid API dump:", data)
        return None

    # --- AUTO-DETECT USERNAME ---
    try:
        TIKTOK_USER = data["data"]["user"]["unique_id"]
        print("Detected TikTok user:", TIKTOK_USER)
    except Exception as e:
        print("Could not detect TikTok user:", e)
        TIKTOK_USER = "unknown"

    videos = data["data"]["videos"]
    print("Loaded", len(videos), "videos from api_dump.txt")
    return videos


# --- Pick best cover ---
def pick_best_cover(video):
    fields = ["cover", "origin_cover", "dynamic_cover", "share_cover"]
    candidates = []

    for field in fields:
        url = video.get(field)
        if url:
            candidates.append(url)

            if url.endswith(".heic"):
                candidates.append(url.replace(".heic", ".jpg"))
                candidates.append(url.replace(".heic", ".jpeg"))

    if "images" in video:
        candidates.extend(video["images"])

    for url in candidates:
        if url and not url.endswith(".heic"):
            return url

    return video.get("cover")


# --- Download & convert cover ---
def download_and_convert_cover(url):
    print("Downloading cover:", url)

    try:
        r = requests.get(url, timeout=10)
    except Exception as e:
        print("Cover download error:", e)
        return None

    if r.status_code != 200:
        print("Cover HTTP error:", r.status_code)
        return None

    content_type = r.headers.get("Content-Type", "").lower()

    if "heic" in content_type or url.endswith(".heic"):
        print("HEIC detected — converting")

        with open("cover.heic", "wb") as f:
            f.write(r.content)

        try:
            subprocess.run(["heif-convert", "cover.heic", "cover.jpg"], check=True)
        except Exception as e:
            print("HEIF convert failed:", e)
            return None

        with open("cover.jpg", "rb") as f:
            return BytesIO(f.read())

    return BytesIO(r.content)


# --- Send Discord embed ---
def send_embed(video):
    video_id = video["video_id"]
    title = video["title"]

    cover_url = pick_best_cover(video)
    if not cover_url:
        print("No valid cover")
        return False

    cover_file = download_and_convert_cover(cover_url)
    if not cover_file:
        return False

    files = {"file": ("cover.jpg", cover_file, "image/jpeg")}
    image_block = {"url": "attachment://cover.jpg"}

    # Universal TikTok link — działa zawsze
    video_url = f"https://www.tiktok.com/video/{video_id}"

    embed = {
        "embeds": [
            {
                "title": f"New TikTok video by @{TIKTOK_USER}",
                "description": title,
                "url": video_url,
                "color": 0x00FFFF,
                "image": image_block
            }
        ]
    }

    resp = requests.post(
        WEBHOOK_URL,
        data={"payload_json": json.dumps(embed)},
        files=files
    )

    print("Discord status:", resp.status_code)
    print("Discord response:", resp.text)

    return resp.status_code in (200, 204)


# --- Main ---
def main():
    ensure_memory_file()
    memory_ids = load_memory()

    videos = get_latest_videos()
    if not videos:
        print("No videos loaded.")
        return

    latest_ids = [v["video_id"] for v in videos]
    new_ids = [vid for vid in latest_ids if vid not in memory_ids]

    print("Found", len(new_ids), "new videos.")

    for vid in reversed(videos):
        if vid["video_id"] in new_ids:
            if send_embed(vid):
                time.sleep(2)

    memory_ids.extend(new_ids)
    memory_ids = memory_ids[-100:]
    save_memory(memory_ids)

    print("Memory updated.")


if __name__ == "__main__":
    main()
