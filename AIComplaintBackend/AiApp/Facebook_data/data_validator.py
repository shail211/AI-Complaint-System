import re
import requests
from config import Config


class DataValidator:
    def validate_post_data(self, post):
        """Validate Facebook post data structure"""
        required_fields = ["id"]
        for field in required_fields:
            if field not in post:
                print(f"⚠️  Missing required field '{field}' in post")
                return False
        return True

    def aggressive_clean_message_text(self, message):
        """Minimal cleaning - just remove TagusComplaint"""
        if not message:
            return ""

        # Only remove TagusComplaint references
        cleaned = re.sub(r"\bTagusComplaint\b", "", message, flags=re.IGNORECASE)
        cleaned = re.sub(r"#TagusComplaint", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        if cleaned != message.strip():
            print(f"   🧹 Removed TagusComplaint: '{message}' → '{cleaned}'")

        return cleaned

    def validate_media_urls(self, media):
        """Validate media URLs and preserve all media types"""
        valid_media = {"images": [], "videos": [], "links": [], "other_attachments": []}

        # Validate each media type
        for media_type in ["images", "videos", "links", "other_attachments"]:
            for item in media.get(media_type, []):
                if media_type == "other_attachments":
                    valid_media[media_type].append(item)
                else:
                    if self.is_valid_url(item.get("url", "")):
                        valid_media[media_type].append(item)

        return valid_media

    def is_valid_url(self, url):
        """Check if URL is valid and accessible"""
        if not url or not url.startswith("http"):
            return False

        try:
            response = requests.head(url, timeout=5)
            return response.status_code == 200
        except:
            return False
