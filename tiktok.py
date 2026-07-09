import os
import requests
from datetime import datetime

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


# --- Fix TikTok HEIC preset → JPG ---
def fix_heic_cover(cover):
    if not cover:
        return None

    if ".heic" not in cover:
        return cover

    print("HEIC detected, converting preset to JPG:", cover)

    # Zamiana presetów HEIC → JPG (działa na TikTok/TikWM)
    cover = cover.replace("q72.heic", "q72.jpg")
    cover = cover.replace("cover:0:480:q72.heic", "cover:0:480:q72.jpg")
    cover = cover.replace("photomode-c-cover:0:480:q72.heic", "photomode-c-cover:0:480:q72.jpg")

    # Fallback wymuszający JPG
    if "image_type=" not in cover:
        cover += "&image_type=jpg"

    return cover


# --- Fetch TikTok videos ---
def get_latest_videos():
    api_url = f"https://www.tikwm.com/api/user/posts?unique_id={TIKTOK_USER}&count=12"

    print("\n--- DEBUG: Fetching TikTok API ---")
    print("URL:", api_url)

    try:
        r = requests.get(api_url, timeout=10)
    except Exception as e:
        print("Request exception:", e)
        append_log("RequestException", str(e))
        return None

    print("HTTP status:", r.status_code)

    if r.status_code != 200:
        print("API error:", r.status_code)
        print("Raw response text:\n", r.text[:2000])
        append_log(r.status_code, r.text)
        return None

    try:
        data = r.json()
    except Exception as e:
        print("JSON parse error:", e)
        print("Raw response text:\n", r.text[:2000])
        append_log("JSONDecodeError", r.text)
        return None

    if data.get("code") != 0:
        print("TikWM returned error:", data)
        append_log("TikWMError", str(data))
        return None

    videos = data["data"]["videos"]
    print("--- DEBUG: Found", len(videos), "videos ---")

    return videos


# --- Send Discord embed ---
def send_embed(video):
    video_id = video["video_id"]
    title = video["title"]
    cover = fix_heic_cover("https://www.tikwm.com" + video["cover"])
    video_url = f"https://www.tiktok.com/@{TIKTOK_USER}/video/{video_id}"

    embed = {
        "embeds": [
            {
                "title": f"New TikTok video by @{TIKTOK_USER}",
                "description": title,
                "url": video_url,
                "color": 0x00FFFF,
                "image": {"url": cover} if cover else {}
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

    # Bierzemy najnowszy
    new_video = next(v for v in videos if v["video_id"] == new_ids[0])

    send_embed(new_video)

    # Aktualizacja pamięci
    updated_memory = latest_ids[:12]
    save_memory(updated_memory)
    print("Memory updated.")


if __name__ == "__main__":
    main()
