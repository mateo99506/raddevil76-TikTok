import os
import requests

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
TIKTOK_USER = "raddevil76"
SAVE_FILE = "last.txt"


def send_no_data(reason=""):
    msg = "No data" if not reason else f"No data ({reason})"
    requests.post(WEBHOOK_URL, json={"content": msg})
    print("Sent:", msg)


def get_latest_videos(count=3):
    try:
        api_url = f"https://www.tikwm.com/api/user/posts?unique_id={TIKTOK_USER}&count={count}"
        r = requests.get(api_url, timeout=10)

        if r.status_code != 200:
            return None

        data = r.json()
        if data.get("data") is None:
            return None

        videos = data["data"].get("videos")
        if not videos:
            return None

        result = []
        for video in videos[:count]:
            result.append({
                "id": video["video_id"],
                "title": video.get("title", "No description"),
                "cover": "https://www.tikwm.com" + video.get("cover", ""),
            })

        return result

    except Exception as e:
        print("API error:", e)
        return None


def save_videos_to_file(videos):
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            for v in videos:
                f.write(v["id"] + "\n")
        print("Saved video IDs to last.txt")
    except Exception as e:
        print("File save error:", e)


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
    videos = get_latest_videos(count=3)
    if not videos:
        send_no_data("API")
        return

    # Save IDs to file (overwrite)
    save_videos_to_file(videos)

    # Send each video in a separate embed
    for video in videos:
        send_embed(video)


if __name__ == "__main__":
    main()
