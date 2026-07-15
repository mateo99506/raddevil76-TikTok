import os
import requests
from datetime import datetime
import subprocess
from io import BytesIO
import json
import time

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
TIKTOK_USER = "raddevil76"

MEMORY_FILE = "memory.txt"
LOG_FILE = "log.txt"


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


# --- Append log (max 1000 lines) ---
def append_log(status, raw_text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{timestamp} | HTTP status: {status} | Raw response: {raw_text[:2000]}\n"

    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []

    lines.append(entry)

    if len(lines) > 1000:
        lines = lines[-1000:]

    with open(LOG_FILE, "w") as f:
        f.writelines(lines)


# --- Download cover and convert HEIC → JPG using ImageMagick ---
def download_and_convert_cover(url):
    print("Downloading cover:", url)

    try:
        r = requests.get(url, timeout=10)
    except Exception as e:
        print("Cover download error:", e)
        append_log("CoverDownloadError", str(e))
        return None

    if r.status_code != 200:
        print("Cover HTTP error:", r.status_code)
        append_log(r.status_code, r.text)
        return None

    content_type = r.headers.get("Content-Type", "").lower()

    # HEIC → convert via ImageMagick
    if "heic" in content_type or url.endswith(".heic"):
        print("HEIC detected — converting via ImageMagick")

        with open("cover.heic", "wb") as f:
            f.write(r.content)

        try:
            subprocess.run(
                ["heif-convert", "cover.heic", "cover.jpg"],
                check=True
            )
            print("HEIC converted using heif-convert")
        except Exception as e:
            print("heif-convert failed:", e)
            append_log("HEIFConvertError", str(e))
            return None

        with open("cover.jpg", "rb") as f:
            return BytesIO(f.read())

    # JPG/PNG → return raw bytes
    print("Cover is already JPG/PNG")
    return BytesIO(r.content)


# --- Fetch TikTok videos ---
def get_latest_videos():
    api_url = f"https://www.tikwm.com/api/user/posts?unique_id={TIKTOK_USER}&count=12"
    
    print("\n--- DEBUG: Fetching TikTok API ---")
    print("URL:", api_url)

    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper()
        r = scraper.get(api_url, timeout=10)
    except Exception as e:
        print("Request exception:", e)
        append_log("RequestException", str(e))
        return None

    print("HTTP status:", r.status_code)

    if r.status_code != 200:
        print("API error:", r.status_code)
        append_log(r.status_code, r.text)
        return None

    try:
        data = r.json()
    except Exception as e:
        print("JSON parse error:", e)
        append_log("JSONDecodeError", r.text)
        return None

    if data.get("code") != 0:
        print("TikWM returned error:", data)
        append_log("TikWMError", str(data))
        return None

    videos = data["data"]["videos"]
    print("--- DEBUG: Found", len(videos), "videos ---")

    return videos

# --- Search JPG file ---
def pick_best_cover(video):
    candidates = []
    
    fields = [
        "cover",
        "origin_cover",
        "dynamic_cover",
        "share_cover"
    ]

    for field in fields:
        url = video.get(field)
        if url:
            candidates.append(url)

            if url.endswith(".heic"):
                jpeg_url = url.replace(".heic", ".jpeg")
                jpg_url = url.replace(".heic", ".jpg")
                candidates.append(jpeg_url)
                candidates.append(jpg_url)

    if "images" in video and isinstance(video["images"], list):
        for img in video["images"]:
            candidates.append(img)

    for url in candidates:
        if url and not url.endswith(".heic"):
            return url

    return video.get("cover")

# --- Send Discord embed with local JPG file ---
def send_embed(video):
    video_id = video["video_id"]
    title = video["title"]

    # FIX: cover URL is already absolute
    cover_url = pick_best_cover(video)

    if cover_url is None:
        print("All cover formats are HEIC — skipping video")
        return False

    cover_file = download_and_convert_cover(cover_url)

    if cover_file is None:
        print("Cover invalid — skipping this video and NOT saving ID")
        return False

    files = {"file": ("cover.jpg", cover_file, "image/jpeg")}
    image_block = {"url": "attachment://cover.jpg"}
    
    video_url = f"https://www.tiktok.com/@{TIKTOK_USER}/video/{video_id}"

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

    print("Sending embed:", embed)

    resp = requests.post(
        WEBHOOK_URL,
        data={"payload_json": json.dumps(embed)},
        files=files
    )

    print("Discord status:", resp.status_code)
    print("Discord response:", resp.text)

    if resp.status_code not in (200, 204):
        print("Discord rejected message — NOT saving ID")
        return False

    return True

# --- Main ---
def main():
    ensure_memory_file()

    memory_ids = load_memory()
    print("Memory IDs:", memory_ids)

    videos = get_latest_videos()
    if not videos:
        print("No videos returned.")
        return

    latest_ids = [v["video_id"] for v in videos]
    print("Latest IDs:", latest_ids)

    new_ids = [vid for vid in latest_ids if vid not in memory_ids]
    print("Found", len(new_ids), "new videos.")

    if not new_ids:
        print("No new videos.")
        return

    # --- SEND ALL NEW VIDEOS WITH 2-SECOND DELAY ---
    for vid in reversed(videos):
        if vid["video_id"] in new_ids:
            if send_embed(vid):
                print("Waiting 2 seconds before next message...")
                time.sleep(2)
            else:
                print("Skipping video — cover invalid, not saving ID")
                continue

    # Update memory
    memory_ids.extend(new_ids)
    
    if len(memory_ids) > 100:
        memory_ids = memory_ids[-100:]
    
    save_memory(memory_ids)
    print("Memory updated (max 100 entries).")


if __name__ == "__main__":
    main()
