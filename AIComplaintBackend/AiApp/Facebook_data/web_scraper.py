import requests
import re
from bs4 import BeautifulSoup


class WebScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def get_user_name(self, url):
        """Your exact get_user_name function"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
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

    def get_media_from_permalink(self, permalink_url):
        """Get additional media by scraping the permalink"""
        try:
            response = requests.get(permalink_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, "html.parser")
            scraped_media = {"images": [], "videos": []}

            # Look for Open Graph images
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"):
                scraped_media["images"].append(
                    {
                        "url": og_image.get("content"),
                        "type": "og_image",
                        "title": "Open Graph Image",
                    }
                )

            # Look for Open Graph videos
            og_video = soup.find("meta", property="og:video")
            if og_video and og_video.get("content"):
                scraped_media["videos"].append(
                    {
                        "url": og_video.get("content"),
                        "type": "og_video",
                        "title": "Open Graph Video",
                    }
                )

            # Look for video URLs in HTML
            html_content = str(soup)
            video_patterns = [
                r'https://video\.xx\.fbcdn\.net/[^"\']+\.mp4',
                r'"source":"(https://[^"]+\.mp4)"',
            ]

            for pattern in video_patterns:
                matches = re.findall(pattern, html_content)
                for match in matches:
                    if match not in [v["url"] for v in scraped_media["videos"]]:
                        scraped_media["videos"].append(
                            {
                                "url": match,
                                "type": "html_scraped_video",
                                "title": "Scraped Video",
                            }
                        )

            return scraped_media
        except Exception as e:
            return {"images": [], "videos": []}
