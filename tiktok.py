import os
import re
import json
import time
import requests
from datetime import datetime
from io import BytesIO
import subprocess

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
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


# --- Fetch TikTok profile page and extract SIGI_STATE ---
def fetch_sigistate():
    url = f"https://www.tiktok.com/@{TIKTOK_USERNAME}?lang=en"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.tiktok.com/",
    }

    print("\n--- DEBUG: Fetching TikTok Web ---")
    print("URL:", url)

    try:
        r = requests.get(url, headers=headers, timeout=15)
    except Exception as e:
        print("Request exception:", e)
        append_log("RequestException", str(e))
        return None

    print("HTTP status:", r.status_code)

    if r.status_code != 200:
        print("TikTok HTTP error:", r.status_code)
        append_log(r.status_code, r.text)
        return None

    html = r.text

    # Szukamy window['SIGI_STATE'] = {...};
    m = re.search(r"window

    \['SIGI_STATE'\]
    
    \s*=\s*(\{.*?\});", html, re.DOTALL)
        if not m:
            print("SIGI_STATE not found in HTML")
            append_log("NoSIGI_STATE", html[:2000])
            return None
    
        sigi_raw = m.group(1)
    
        try:
            sigi = json.loads(sigi_raw)
        except Exception as e:
            print("SIGI_STATE JSON parse error:", e)
            append_log("SIGI_JSONError", sigi_raw[:2000])
            return None
    
        return sigi
    
    
    # --- Extract videos from SIGI_STATE ---
    def get_latest_videos_from_sigi():
        sigi = fetch_sigistate()
        if not sigi:
            return None
    
        item_module = sigi.get("ItemModule", {})
        if not isinstance(item_module, dict) or not item_module:
            print("ItemModule empty or missing")
            append_log("NoItemModule", json.dumps(sigi)[:2000])
            return None
    
        # ItemModule: { videoId: { ... } }
        videos = list(item_module.values())
    
        # Sort by createTime (descending)
        def sort_key(v):
            return int(v.get("createTime", 0))
    
        videos.sort(key=sort_key, reverse=True)
    
        print("--- DEBUG: Found", len(videos), "videos in ItemModule ---")
        return videos
    
    
    # --- Pick best cover from ItemModule video object ---
    def pick_best_cover(video):
        # TikTok Web: video["video"]["cover"] / "dynamicCover" / "originCover"
        v = video.get("video", {})
        for field in ["cover", "dynamicCover", "originCover"]:
            url = v.get(field)
            if url:
                return url
        return None
    
    
    # --- Send Discord embed with local JPG file ---
    def send_embed(video):
        video_id = video.get("id")
        if not video_id:
            print("No video ID — skipping")
            return False
    
        title = video.get("desc") or "New TikTok video"
    
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
    
        videos = get_latest_videos_from_sigi()
        if not videos:
            print("No videos returned from SIGI_STATE.")
            return
    
        latest_ids = [v.get("id") for v in videos if v.get("id")]
        print("Latest IDs:", latest_ids)
    
        new_ids = [vid for vid in latest_ids if vid not in memory_ids]
        print("Found", len(new_ids), "new videos.")
    
        if not new_ids:
            print("No new videos.")
            return
    
        # --- SEND ALL NEW VIDEOS WITH 2-SECOND DELAY ---
        for vid in videos:
            vid_id = vid.get("id")
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
