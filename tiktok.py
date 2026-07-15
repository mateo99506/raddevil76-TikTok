import os
import requests
from datetime import datetime
import subprocess
from io import BytesIO
import json
import time

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

# TikTok Mobile API – wewnętrzne ID użytkownika (nie @nazwa)
TIKTOK_USER_ID = "7503894081589707798"
TIKTOK_USERNAME = "raddevil76"

MEMORY_FILE = "memory.txt"
LOG_FILE = "log.txt"


# --- Ensure memory file exists ---
def ensure_memory_file():
    if not os.path.exists(MEMORY_FILE):
        open(MEMORY_FILE, "w").close()


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

    # HEIC → convert via heif-convert
    if "heic" in content_type or url.endswith(".heic"):
        print("HEIC detected — converting via heif-convert")

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


# --- Pick best cover from Mobile API video object ---
def pick_best_cover(video):
    # TikTok Mobile API: video["video"]["cover"]["url_list"] / origin_cover / dynamic_cover
    candidates = []

    v = video.get("video", {})

    for field in ["cover", "origin_cover", "dynamic_cover"]:
        obj = v.get(field)
        if obj and isinstance(obj, dict):
            urls = obj.get("url_list", [])
            for u in urls:
                candidates.append(u)

    # fallback: share_info / misc
    share_info = video.get("share_info", {})
    if isinstance(share_info, dict):
        cover_url = share_info.get("share_cover")
        if cover_url:
            candidates.append(cover_url)

    # wybierz pierwsze nie-HEIC
    for url in candidates:
        if url and not url.endswith(".heic"):
            return url

    # jeśli wszystko HEIC – zwróć pierwsze
    return candidates[0] if candidates else None


# --- Fetch TikTok videos via Mobile API ---
def get_latest_videos():
    api_url = "https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/aweme/post/"

    params = {
        "user_id": TIKTOK_USER_ID,
        "count": 12,
        "max_cursor": 0,
        "aid": 1988,
    }

    headers = {
        "User-Agent": "com.ss.android.ugc.aweme/700 (Linux; Android 12)",
        "Accept": "application/json",
    }

    print("\n--- DEBUG: Fetching TikTok Mobile API ---")
    print("URL:", api_url)
    print("Params:", params)

    try:
        r = requests.get(api_url, params=params, headers=headers, timeout=10)
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

    if "aweme_list" not in data:
        print("No aweme_list in response")
        append_log("NoAwemeList", json.dumps(data)[:2000])
        return None

    videos = data["aweme_list"]
    print("--- DEBUG: Found", len(videos), "videos ---")

    return videos


# --- Send Discord embed with local JPG file ---
def send_embed(video):
    video_id = video.get("aweme_id")
    if not video_id:
        print("No aweme_id — skipping")
        return False

    # tytuł – z desc lub share_info
    title = video.get("desc") or video.get("share_info", {}).get("share_title") or "New TikTok video"

    cover_url = pick_best_cover(video)

    if cover_url is None:
        print("No valid cover URL — skipping video")
        return False

    cover_file = download_and_convert_cover(cover_url)

    if cover_file is None:
        print("Cover invalid — skipping this video and NOT saving ID")
        return False

    files = {"file": ("cover.jpg", cover_file, "image/jpeg")}
    image_block = {"url": "attachment://cover.jpg"}

    video_url = f"https://www.tiktok.com/@{TIKTOK_USERNAME}/video/{video_id}"

    embed = {
        "embeds": [
            {
                "title": f"New TikTok video by @{TIKTOK_USERNAME}",
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
        append_log(resp.status_code, resp.text)
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

    latest_ids = [v.get("aweme_id") for v in videos if v.get("aweme_id")]
    print("Latest IDs:", latest_ids)

    new_ids = [vid for vid in latest_ids if vid not in memory_ids]
    print("Found", len(new_ids), "new videos.")

    if not new_ids:
        print("No new videos.")
        return

    # --- SEND ALL NEW VIDEOS WITH 2-SECOND DELAY ---
    for vid in reversed(videos):
        vid_id = vid.get("aweme_id")
        if not vid_id:
            continue

        if vid_id in new_ids:
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
