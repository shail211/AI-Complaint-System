import requests
import os
import time
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime

load_dotenv()

PAGE_ID = os.getenv("PAGE_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")


def get_user_name(url):
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            timeout=10,
        )
        soup = BeautifulSoup(response.content, "html.parser")
        title = soup.find("title").get_text().strip()
        print(f"Title : {title}")

        # If | exists
        if "|" in title:
            left, right = title.split("|", 1)
            right = right.strip()
            if "TagusComplaint" not in right:
                return right
            else:
                return left.strip()

        # If - exists
        if "-" in title:
            left, right = title.split("-", 1)
            left = left.strip()
            if left and "TagusComplaint" not in left:
                return left
            else:
                return right.strip()

        # Fallback: remove TagusComplaint if repeated
        cleaned_title = title.replace("TagusComplaint", "").strip()
        return cleaned_title if cleaned_title else "Name not found"

    except:
        return "Error extracting name"


def get_paginated_data(url, params):
    all_data = []
    while url:
        response = requests.get(url, params=params)
        data = response.json()

        if "data" in data:
            all_data.extend(data["data"])

        url = data.get("paging", {}).get("next")
        params = {}

    return all_data


def process_posts(posts):
    clean_data = []

    for post in posts:
        user_name = get_user_name(post.get("permalink_url"))

        # Fallback to API name if scraping fails
        if user_name == "Error extracting name" or user_name == "Name not found":
            user_name = post.get("from", {}).get("name", "Unknown")
            source = "api_fallback"
        else:
            source = "scraped"

        post_entry = {
            "post_id": post.get("id"),
            "name": user_name,
            "name_source": source,
            "message": post.get("message", ""),
            "created_time": post.get("created_time"),
            "permalink": post.get("permalink_url"),
            "media": [],
        }

        if "full_picture" in post:
            post_entry["media"].append(
                {"type": "image", "url": post.get("full_picture")}
            )

        clean_data.append(post_entry)

    return clean_data


def save_to_json(data, filename="mentions_clean.json", folder="output_data"):
    os.makedirs(folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_filename = f"{filename.replace('.json', '')}_{timestamp}.json"
    file_path = os.path.join(folder, full_filename)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"\n✅ Clean data saved to {file_path}")


def facebook_mentions(minutes=None, hours=None, days=None):
    current_time = int(time.time())

    if minutes is None and hours is None and days is None:
        minutes = 10

    total_seconds = 0
    if minutes:
        total_seconds += minutes * 60
    if hours:
        total_seconds += hours * 3600
    if days:
        total_seconds += days * 86400

    since_time = current_time - total_seconds

    params_common = {
        "access_token": ACCESS_TOKEN,
        "limit": 100,
        "since": since_time,
    }

    tagged_url = f"https://graph.facebook.com/v23.0/{PAGE_ID}/tagged"
    tagged_posts = get_paginated_data(
        tagged_url,
        {
            **params_common,
            "fields": "id,message,from,created_time,permalink_url,full_picture,picture",
        },
    )

    clean_data = process_posts(tagged_posts)
    save_to_json(clean_data, filename="mentions_clean.json", folder="output_data")


# facebook_mentions(days=5, hours=0, minutes=15)
