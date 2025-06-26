import os
import requests
from dotenv import load_dotenv

# Load Pexels API key
load_dotenv("../.env")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
if not PEXELS_API_KEY:
    raise Exception("PEXELS_API_KEY not found in .env file")

PEXELS_IMAGE_URL = "https://api.pexels.com/v1/search"
PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"

def search_pexels(query, media_type="image", per_page=3):
    headers = {"Authorization": PEXELS_API_KEY}
    url = PEXELS_IMAGE_URL if media_type == "image" else PEXELS_VIDEO_URL
    params = {"query": query, "per_page": per_page}
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()
    if media_type == "image":
        return [photo["src"]["medium"] for photo in data.get("photos", [])]
    else:
        return [video["video_files"][0]["link"] for video in data.get("videos", [])]

def main():
    print("🔎 Searching Pexels for B-rolls and images for YouTube Reel script...\n")

    search_terms = {
        "thumbnail": ["Trump TikTok logo", "TikTok future", "Trump question emoji"],
        "hook": ["Trump breaking news", "TikTok deadline", "Trump press conference"],
        "act1": ["news headlines", "Trump speaking", "TikTok logo"],
        "act2": ["protest", "TikTok influencer", "app store", "China flag"],
        "act3": ["TikTok trends", "data privacy", "Trump signing document", "US flag vs China flag"],
        "cta": ["TikTok UI", "comment section"]
    }

    for section, queries in search_terms.items():
        print(f"\n--- {section.upper()} ---")
        for q in queries:
            print(f"\n🔹 Query: {q}")
            try:
                images = search_pexels(q, "image", per_page=2)
                print("  Images:")
                for img in images:
                    print(f"    {img}")
                videos = search_pexels(q, "video", per_page=1)
                print("  Videos:")
                for vid in videos:
                    print(f"    {vid}")
            except Exception as e:
                print(f"  ⚠️  Error fetching for '{q}': {e}")

if __name__ == "__main__":
    main()