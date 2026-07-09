import os
import requests
from datetime import datetime
import subprocess
from io import BytesIO

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
TIKTOK_USER = "raddevil76"

MEMORY_FILE = "memory.txt"
LOG_FILE = "log.txt"


def ensure_memory_file():
    if not os.path.exists(MEMORY_FILE):
        open(MEMORY_FILE, "w").close()
        print("Created empty memory.txt")
    else:
        print("memory.txt already exists")


def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            data = f.read().strip()
            if not data:
                return []
            return data.split(",")
    except:
        return []


def save_memory(ids):
    with open(MEMORY_FILE, "w") as f:
        f.write(",".join(ids))


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

    # Save HEIC or JPG temporarily
    if "heic" in content_type or url.endswith(".heic"):
        print("HEIC detected — converting via ImageMagick")

        with open("cover.heic", "wb") as f:
            f.write(r.content)

        try:
            subprocess.run(["convert", "cover.heic", "cover.jpg"], check=True)
        except Exception as e:
            print("ImageMagick conversion error:", e)
            append_log("ImageMagickError", str(e))
            return None

        with open("cover.jpg", "rb") as f:
            return BytesIO(f.read())

    else:
        print("Cover is already JPG/PNG")
        return BytesIO(r.content)


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


def send_embed(video):
    video_id = video["video_id"]
    title = video["title"]

    cover_url = "https://www.tikwm.com" + video["cover"]
    cover_file = download_and_convert_cover(cover_url)

    if cover_file is None:
        print("Cover conversion failed — sending embed without image")
        files = None
        image_block = {}
    else:
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
    resp = requests.post(WEBHOOK_URL, data={"payload_json": str(embed)}, files=files)
    print("Discord status:", resp.status_code)
    print("Discord response:", resp.text)


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

    new_video = next(v for v in videos if v["video_id"] == new_ids[0])

    send_embed(new_video)

    updated_memory = latest_ids[:12]
    save_memory(updated_memory)
    print("Memory updated.")


if __name__ == "__main__":
    main()
