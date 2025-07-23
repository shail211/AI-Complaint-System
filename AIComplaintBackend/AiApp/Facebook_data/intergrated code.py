import requests
import os
import time
import json
import re
import traceback
import logging
from datetime import datetime, timedelta
from functools import wraps
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from groq import Groq

# Load environment variables
load_dotenv()

# Configuration
PAGE_ID = os.getenv("PAGE_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "gemma2-9b-it"

# Department and Officer mapping
DEPARTMENTS_OFFICERS = """
IT Department:
- Aayush Pradhan
- Kinley Bhutia

Land Revenue & Disaster Management Department:
- Dawa Tshering Bhutia
- Pema Dorjee Lepcha

Road and Bridges Department:
- Mingma Sherpa
- Tashi Lepcha

Education Department:
- Dolma Bhutia
- Sonika Chettri

Forest & Environment Department:
- Lobsang Bhutia
- Nima Sherpa

Social Welfare Department:
- Pema Lhamu Bhutia
- Tashi Deki Lepcha

Rural Development Department:
- Ramesh Chhetri
- Pem Dorjee Sherpa

Excise Department:
- Karma Bhutia
- Sonam Lepcha
"""

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)


# ==================== ERROR HANDLER ====================
class ErrorHandler:
    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 2

    def retry_on_failure(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(self.max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    if attempt == self.max_retries - 1:
                        print(f"❌ Final attempt failed: {str(e)}")
                        raise
                    print(
                        f"⚠️  Attempt {attempt + 1} failed, retrying in {self.retry_delay}s..."
                    )
                    time.sleep(self.retry_delay)
                except Exception as e:
                    print(f"❌ Unexpected error: {str(e)}")
                    raise

        return wrapper


# ==================== RATE LIMITER ====================
class RateLimiter:
    def __init__(self, max_requests_per_hour=200):
        self.max_requests = max_requests_per_hour
        self.requests = []
        self.facebook_delay = 0.5
        self.groq_delay = 1.0

    def wait_if_needed(self, api_type="facebook"):
        now = datetime.now()

        # Remove requests older than 1 hour
        self.requests = [
            req_time
            for req_time in self.requests
            if now - req_time < timedelta(hours=1)
        ]

        # Check if we're at the limit
        if len(self.requests) >= self.max_requests:
            sleep_time = 3600
            print(f"⚠️  Rate limit reached. Waiting {sleep_time/60:.1f} minutes...")
            time.sleep(sleep_time)

        # API-specific delays
        if api_type == "facebook":
            time.sleep(self.facebook_delay)
        elif api_type == "groq":
            time.sleep(self.groq_delay)

        self.requests.append(now)


# ==================== LOGGER ====================
class Logger:
    def __init__(self, log_level=logging.INFO):
        self.logger = logging.getLogger("facebook_mentions")
        self.logger.setLevel(log_level)

        # Create logs directory if it doesn't exist
        if not os.path.exists("logs"):
            os.makedirs("logs")

        # File handler
        log_filename = f"logs/facebook_mentions_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(log_level)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)

        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def log_api_call(self, endpoint, response_code, post_count=0):
        self.logger.info(
            f"API Call: {endpoint} | Response: {response_code} | Posts: {post_count}"
        )

    def log_complaint_analysis(self, post_id, is_complaint, priority=None):
        if is_complaint:
            self.logger.info(
                f"Complaint detected: Post {post_id} | Priority: {priority}"
            )
        else:
            self.logger.debug(f"No complaint: Post {post_id}")

    def log_error(self, error, context=""):
        self.logger.error(f"Error in {context}: {str(error)}")


# ==================== DATA VALIDATOR ====================
class DataValidator:
    def validate_post_data(self, post):
        required_fields = ["id"]
        for field in required_fields:
            if field not in post:
                print(f"⚠️  Missing required field '{field}' in post")
                return False
        return True

    def aggressive_clean_message_text(self, message):
        """Aggressively clean TagusComplaint references that cause misconceptions"""
        if not message:
            return ""

        original_message = message

        # Step 1: Remove all TagusComplaint variations
        tagus_patterns = [
            r"\bTagusComplaint\b",
            r"\bTagus\s*Complaint\b",
            r"\btagus\s*complaint\b",
            r"#TagusComplaint",
            r"#taguscomplaint",
            r"@TagusComplaint",
            r"TagusComplaint\s+\w+",  # TagusComplaint followed by any word
            r"\w+\s+TagusComplaint",  # Any word followed by TagusComplaint
        ]

        cleaned = message
        for pattern in tagus_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        # Step 2: Remove common test/greeting patterns
        test_patterns = [
            r"\btest\b",
            r"\btesting\b",
            r"\bhey\b",
            r"\bhi\b",
            r"\bhello\b",
            r"\bbro\b",
            r"\bsee\s+this\b",
            r"\bhow\b(?!\s+to)",  # "how" but not "how to"
            r"\blikes?\b",
            r"\bvideo\s*\d*\b",
            r"\bimage\s*\d*\b",
            r"\bvideos\b",
            r"where\s+is\s+my\s+post",
            r"random\s+characters?",
            r"^[a-z]{3,}$",  # Single random word
        ]

        for pattern in test_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        # Step 3: Clean up whitespace and punctuation
        cleaned = re.sub(r"[^\w\s]", " ", cleaned)  # Replace punctuation with spaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Log what was cleaned
        if cleaned != original_message.strip():
            print(f"   🧹 Cleaned: '{original_message}' → '{cleaned}'")

        return cleaned

    def validate_media_urls(self, media):
        """Fixed to preserve all media types including other_attachments"""
        valid_media = {"images": [], "videos": [], "links": [], "other_attachments": []}

        # Validate each media type
        for media_type in ["images", "videos", "links", "other_attachments"]:
            for item in media.get(media_type, []):
                if media_type == "other_attachments":
                    # For other attachments, just copy them without URL validation
                    valid_media[media_type].append(item)
                else:
                    # For images, videos, links, validate URLs
                    if self.is_valid_url(item.get("url", "")):
                        valid_media[media_type].append(item)

        return valid_media

    def is_valid_url(self, url):
        if not url or not url.startswith("http"):
            return False

        try:
            response = requests.head(url, timeout=5)
            return response.status_code == 200
        except:
            return False


# ==================== YOUR EXACT get_user_name FUNCTION ====================
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


# ==================== MEDIA EXTRACTION ====================
def get_media_from_permalink(permalink_url):
    """Get additional media by scraping the permalink"""
    try:
        response = requests.get(
            permalink_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            timeout=10,
        )

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


def extract_media_from_post(post_data):
    """Extract all media (images, videos, links) from a post"""
    media = {"images": [], "videos": [], "links": [], "other_attachments": []}

    # Direct image from post
    if "full_picture" in post_data:
        media["images"].append(
            {
                "url": post_data["full_picture"],
                "type": "post_image",
                "title": "Full Picture",
            }
        )

    # Thumbnail image (if different from full picture)
    if "picture" in post_data and post_data.get("picture") != post_data.get(
        "full_picture"
    ):
        media["images"].append(
            {
                "url": post_data["picture"],
                "type": "post_thumbnail",
                "title": "Thumbnail",
            }
        )

    # Note: Since you're only using the specific fields, attachments processing is limited
    # But keeping this for future compatibility if you add attachment fields
    if "attachments" in post_data and "data" in post_data["attachments"]:
        for attachment in post_data["attachments"]["data"]:
            attachment_type = attachment.get("type", "unknown")

            if attachment_type == "photo":
                if "media" in attachment and "image" in attachment["media"]:
                    media["images"].append(
                        {
                            "url": attachment["media"]["image"].get("src", ""),
                            "type": "attachment_image",
                            "title": attachment.get("title", ""),
                        }
                    )

            elif attachment_type in ["video_inline", "video_autoplay"]:
                if "media" in attachment:
                    if "source" in attachment["media"]:
                        media["videos"].append(
                            {
                                "url": attachment["media"]["source"],
                                "type": "attachment_video",
                                "title": attachment.get("title", ""),
                            }
                        )
                    if "image" in attachment["media"]:
                        media["images"].append(
                            {
                                "url": attachment["media"]["image"].get("src", ""),
                                "type": "video_thumbnail",
                                "title": attachment.get("title", "") + " (thumbnail)",
                            }
                        )

            elif attachment_type in ["share", "link"]:
                media["links"].append(
                    {
                        "url": attachment.get("url", ""),
                        "title": attachment.get("title", ""),
                        "description": attachment.get("description", ""),
                        "type": "shared_link",
                    }
                )

            else:
                media["other_attachments"].append(
                    {
                        "type": attachment_type,
                        "title": attachment.get("title", ""),
                        "url": attachment.get("url", ""),
                    }
                )

    return media


# ==================== IMPROVED AI COMPLAINT ANALYSIS ====================
def strict_pre_filter(text):
    """Ultra-strict pre-filtering to eliminate obvious non-complaints"""
    if not text or len(text.strip()) < 15:  # Increased minimum length
        return False, "Text too short (needs detailed description)"

    # Automatic rejections - these are NEVER complaints
    auto_reject_patterns = [
        r"^\s*(test|testing)\s*$",
        r"^\s*(hi|hello|hey)\s*$",
        r"^\s*video\s*\d*\s*$",
        r"^\s*image\s*\d*\s*$",
        r"^\s*videos?\s*$",
        r"^\s*images?\s*$",
        r"^\s*likes?\s*$",
        r"^\s*how\s*$",
        r"^\s*see\s+this\s*$",
        r"^\s*bro\s*$",
        r"where\s+is\s+my\s+post",
        r"^\s*[a-z]{1,20}\s*$",  # Single random words
        r"^[^a-zA-Z]*$",  # Only special characters/numbers
        r"random\s+characters",
        r"only.*test",
        r"this\s+is.*test",
    ]

    for pattern in auto_reject_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False, f"Auto-rejected: {pattern}"

    # Must contain complaint keywords to proceed
    complaint_keywords = [
        r"\b(problem|issue|broken|damaged|not\s+working|failed|failure)\b",
        r"\b(complaint|complain|report|fix|repair|solve)\b",
        r"\b(poor|bad|terrible|awful|delayed|slow|stopped)\b",
        r"\b(service|department|office|government|public)\b",
        r"\b(road|water|electricity|power|permit|license)\b",
        r"\b(help|assistance|action|urgent|emergency)\b",
    ]

    has_complaint_keywords = False
    for pattern in complaint_keywords:
        if re.search(pattern, text, re.IGNORECASE):
            has_complaint_keywords = True
            break

    if not has_complaint_keywords:
        return False, "No complaint-related keywords found"

    # Must have some descriptive detail (not just keywords)
    word_count = len([word for word in text.split() if len(word) > 2])
    if word_count < 5:  # Needs at least 5 meaningful words
        return False, f"Insufficient detail ({word_count} words, needs 5+)"

    return True, "Passed strict pre-filter"


def is_complaint_ultra_strict(text):
    """Ultra-strict complaint detection requiring substantial details"""

    if not text or not text.strip():
        return False

    # Step 1: Strict pre-filter
    passed_filter, reason = strict_pre_filter(text)
    if not passed_filter:
        print(f"   🚫 Pre-filter rejected: {reason}")
        return False

    print(f"   ✓ Passed pre-filter, analyzing with AI...")

    prompt = f"""
You are an EXTREMELY STRICT government complaint classifier. You must be very conservative and only classify as complaint if there is a CLEAR, DETAILED description of a PUBLIC SERVICE PROBLEM.

STRICT REQUIREMENTS FOR COMPLAINT (ALL must be met):
1. Must describe a SPECIFIC problem with government/public services
2. Must provide DETAILS about the issue (location, what's wrong, how it affects people)
3. Must be requesting government ACTION to fix something
4. Must NOT be just a greeting, test message, or simple question

REJECT these as NOT complaints:
- Test messages ("test", "testing")
- Simple greetings ("hi", "hello", "hey")
- Single words or phrases ("video", "image", "how", "likes")
- Questions about post status ("where is my post")
- Random characters or gibberish
- General appreciation or thanks
- Anything without specific problem description

ONLY ACCEPT as complaints:
- "The road on Main Street has potholes that damage vehicles daily"
- "Water supply has been cut for 3 days in Sector 5, please restore"
- "The government office is closed during posted hours, causing delays"

TEXT: "{text}"

Based on STRICT criteria, is this a genuine detailed government service complaint?
Answer with ONLY "true" or "false":
"""

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are an ultra-strict complaint classifier. Reject anything that isn't a detailed, specific complaint about government services. Be very conservative.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,  # Very low for consistency
            max_tokens=5,
            top_p=0.8,
        )

        response = completion.choices[0].message.content.strip().lower()
        is_complaint = response == "true"

        print(f"   🤖 AI Decision: {response}")
        return is_complaint

    except Exception as e:
        print(f"   ❌ AI Error: {e}")
        return False


def analyze_complaint_detailed(complaint_text):
    """Analyze detailed complaints only"""

    prompt = f"""
You are analyzing a VERIFIED government service complaint. This text has already been confirmed as a genuine complaint with specific details.

COMPLAINT: "{complaint_text}"

Provide detailed analysis:

PRIORITY (1-5):
5 = Life-threatening emergency (safety hazards, medical emergencies)
4 = Critical infrastructure failure (major roads, essential services)
3 = Significant service disruption (affecting many people)
2 = Standard service issues (delays, quality problems)  
1 = Minor issues or suggestions

ANALYSIS REQUIREMENTS:
- sentiment: angry/frustrated/concerned/urgent/neutral
- urgency_level: emergency/high/medium/low
- category: infrastructure/utilities/permits/healthcare/education/transportation/environment/social_services/other
- summary: Concise description of the actual problem
- suggested_actions: Specific actionable steps (minimum 2)

Departments and Officers:
{DEPARTMENTS_OFFICERS}

Respond with JSON format:
{{"priority_score": X, "department": "...", "recommended_officer": "...", "ai_analysis": {{"sentiment": "...", "urgency_level": "...", "category": "...", "summary": "...", "suggested_actions": ["...", "..."]}}}}
"""

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You are analyzing verified complaints with detailed problem descriptions. Provide thorough, actionable analysis.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1024,
            top_p=0.95,
        )

        content = completion.choices[0].message.content
        content = re.sub(r"^``````$", "", content.strip())

        try:
            return json.loads(content)
        except:
            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                return json.loads(match.group(0))
            raise

    except Exception as e:
        print(f"   ❌ Analysis error: {e}")
        return None


# ==================== FACEBOOK API ====================
def get_paginated_data(url, params, rate_limiter, logger):
    """Get all paginated data from Facebook API with rate limiting"""
    all_data = []
    page_count = 0

    while url and page_count < 10:
        try:
            rate_limiter.wait_if_needed("facebook")
            response = requests.get(url, params=params, timeout=30)

            logger.log_api_call(f"Page {page_count + 1}", response.status_code)

            if response.status_code != 200:
                print(f"⚠️  API Error on page {page_count + 1}: {response.status_code}")
                break

            data = response.json()

            if "error" in data:
                print(f"⚠️  Facebook Error: {data['error']}")
                logger.log_error(data["error"], f"Page {page_count + 1}")
                break

            if "data" in data:
                all_data.extend(data["data"])
                print(f"📄 Fetched page {page_count + 1}: {len(data['data'])} posts")

            url = data.get("paging", {}).get("next")
            params = {}
            page_count += 1

        except Exception as e:
            print(f"❌ Error on page {page_count + 1}: {str(e)}")
            logger.log_error(e, f"Page {page_count + 1}")
            break

    return all_data


# ==================== DATA PROCESSING ====================
def prepare_data_for_json(posts, validator, rate_limiter, logger):
    """Prepare posts data for JSON export with strict complaint filtering"""
    json_data = {
        "export_info": {
            "timestamp": datetime.now().isoformat(),
            "total_posts": len(posts),
            "page_id": PAGE_ID,
            "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "posts": [],
    }

    print("🔄 Processing posts for JSON export with STRICT complaint filtering...")

    for i, post in enumerate(posts, 1):
        if not validator.validate_post_data(post):
            continue

        print(f"Processing post {i}/{len(posts)}...")

        # Extract username using your exact function
        username = "Unknown"
        if "permalink_url" in post:
            username = get_user_name(post.get("permalink_url"))

        # Extract media from API
        media = extract_media_from_post(post)

        # Extract additional media from permalink scraping
        if "permalink_url" in post:
            scraped_media = get_media_from_permalink(post.get("permalink_url"))
            # Merge scraped media (avoid duplicates)
            for img in scraped_media["images"]:
                if not any(
                    existing["url"] == img["url"] for existing in media["images"]
                ):
                    media["images"].append(img)

            for vid in scraped_media["videos"]:
                if not any(
                    existing["url"] == vid["url"] for existing in media["videos"]
                ):
                    media["videos"].append(vid)

        # Validate media URLs
        media = validator.validate_media_urls(media)

        # Count media items
        media_count = {
            "images": len(media["images"]),
            "videos": len(media["videos"]),
            "links": len(media["links"]),
            "other_attachments": len(media["other_attachments"]),
            "total": len(media["images"])
            + len(media["videos"])
            + len(media["links"])
            + len(media["other_attachments"]),
        }

        # AGGRESSIVE complaint analysis with TagusComplaint removal
        message = post.get("message", "")
        cleaned_message = validator.aggressive_clean_message_text(message)
        complaint_info = {"is_complaint": False}

        if cleaned_message and cleaned_message.strip():
            print(f"   🔍 STRICT complaint check on cleaned text: '{cleaned_message}'")
            rate_limiter.wait_if_needed("groq")

            # Ultra-strict complaint detection
            if is_complaint_ultra_strict(cleaned_message):
                print(f"   ⚠️  GENUINE COMPLAINT detected! Analyzing...")
                complaint_info["is_complaint"] = True

                rate_limiter.wait_if_needed("groq")
                analysis_result = analyze_complaint_detailed(cleaned_message)

                if analysis_result:
                    complaint_info["analysis"] = analysis_result
                    priority = analysis_result.get("priority_score", "N/A")
                    print(f"   ✅ Detailed complaint analyzed - Priority: {priority}")
                    logger.log_complaint_analysis(post.get("id"), True, priority)
                else:
                    print(f"   ❌ Failed to analyze complaint details")
            else:
                print(f"   ℹ️  NOT a complaint (rejected by strict filters)")
                logger.log_complaint_analysis(post.get("id"), False)
        else:
            print(f"   🚫 Message empty after aggressive cleaning")

        # Prepare post data
        post_data = {
            "post_id": post.get("id", ""),
            "username": username,
            "message": message,
            "cleaned_message": cleaned_message,
            "from_name": post.get("from", {}).get("name", "Unknown"),
            "created_time": post.get("created_time", ""),
            "permalink_url": post.get("permalink_url", ""),
            "media": media,
            "media_count": media_count,
            "complaint": complaint_info,
            "raw_data": {
                "full_picture": post.get("full_picture", ""),
                "picture": post.get("picture", ""),
            },
        }

        json_data["posts"].append(post_data)

    # Add summary statistics
    total_images = sum(
        len(post_data["media"]["images"]) for post_data in json_data["posts"]
    )
    total_videos = sum(
        len(post_data["media"]["videos"]) for post_data in json_data["posts"]
    )
    total_links = sum(
        len(post_data["media"]["links"]) for post_data in json_data["posts"]
    )
    total_complaints = sum(
        1 for post_data in json_data["posts"] if post_data["complaint"]["is_complaint"]
    )

    json_data["summary"] = {
        "total_posts": len(json_data["posts"]),
        "total_images": total_images,
        "total_videos": total_videos,
        "total_links": total_links,
        "total_media_items": total_images + total_videos + total_links,
        "posts_with_media": sum(
            1
            for post_data in json_data["posts"]
            if post_data["media_count"]["total"] > 0
        ),
        "usernames_extracted": sum(
            1
            for post_data in json_data["posts"]
            if post_data["username"]
            not in ["Unknown", "Name not found", "Error extracting name"]
        ),
        "total_complaints": total_complaints,
        "complaint_rate": (
            f"{(total_complaints/len(json_data['posts'])*100):.1f}%"
            if json_data["posts"]
            else "0%"
        ),
    }

    return json_data


# ==================== FILE MANAGEMENT ====================
def save_to_json(data, filename=None):
    """Save data to JSON file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"facebook_mentions_{timestamp}.json"

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"💾 Data saved to: {filename}")
        print(f"📁 File size: {os.path.getsize(filename) / 1024:.1f} KB")
        return filename

    except Exception as e:
        print(f"❌ Error saving JSON: {str(e)}")
        return None


# ==================== DISPLAY FUNCTIONS ====================
def print_media(media):
    """Print media information in a formatted way"""
    if media["images"]:
        print("📷 IMAGES:")
        for i, img in enumerate(media["images"], 1):
            print(f"   {i}. {img['type']}: {img['url']}")
            if img.get("title"):
                print(f"      Title: {img['title']}")

    if media["videos"]:
        print("🎥 VIDEOS:")
        for i, video in enumerate(media["videos"], 1):
            print(f"   {i}. {video['type']}: {video['url']}")
            if video.get("title"):
                print(f"      Title: {video['title']}")

    if media["links"]:
        print("🔗 LINKS:")
        for i, link in enumerate(media["links"], 1):
            print(f"   {i}. {link['type']}: {link['url']}")
            if link.get("title"):
                print(f"      Title: {link['title']}")
            if link.get("description"):
                print(f"      Description: {link['description'][:100]}...")

    if media["other_attachments"]:
        print("📎 OTHER ATTACHMENTS:")
        for i, att in enumerate(media["other_attachments"], 1):
            print(f"   {i}. {att['type']}: {att.get('url', 'No URL')}")
            if att.get("title"):
                print(f"      Title: {att['title']}")


def print_items(posts, title, rate_limiter, validator):
    """Print all items with detailed information"""
    print(f"\n==== {title} ({len(posts)}) ====")

    for i, post in enumerate(posts, 1):
        print(f"\n--- POST #{i} ---")
        print(f"📝 Post ID: {post.get('id', 'No ID')}")

        # Get username using your exact function
        if "permalink_url" in post:
            permalink = post.get("permalink_url")
            print(f"🔗 Permalink: {permalink}")

            user_name = get_user_name(permalink)
            print(f"👤 Username: {user_name}")
        else:
            print(f"👤 Username: Not available")

        # Message and strict complaint analysis
        if "message" in post:
            message = post.get("message", "")
            display_message = message[:200] + "..." if len(message) > 200 else message
            print(f"💬 Original Message: {display_message}")

            # Aggressively clean message
            cleaned_message = validator.aggressive_clean_message_text(message)
            if cleaned_message:
                print(f"🧹 Cleaned Message: {cleaned_message}")

                rate_limiter.wait_if_needed("groq")

                if is_complaint_ultra_strict(cleaned_message):
                    print(f"⚠️  GENUINE COMPLAINT DETECTED!")

                    rate_limiter.wait_if_needed("groq")
                    analysis = analyze_complaint_detailed(cleaned_message)

                    if analysis:
                        print(
                            f"   🎯 Priority: {analysis.get('priority_score', 'N/A')}/5"
                        )
                        print(f"   🏢 Department: {analysis.get('department', 'N/A')}")
                        print(
                            f"   👨‍💼 Officer: {analysis.get('recommended_officer', 'N/A')}"
                        )
                        if "ai_analysis" in analysis:
                            ai_analysis = analysis["ai_analysis"]
                            print(
                                f"   😊 Sentiment: {ai_analysis.get('sentiment', 'N/A')}"
                            )
                            print(
                                f"   ⚡ Urgency: {ai_analysis.get('urgency_level', 'N/A')}"
                            )
                            print(
                                f"   📊 Category: {ai_analysis.get('category', 'N/A')}"
                            )
                            print(f"   📄 Summary: {ai_analysis.get('summary', 'N/A')}")
                else:
                    print(f"ℹ️  NOT a complaint (failed strict validation)")
            else:
                print(
                    f"🚫 Message removed completely after cleaning (contained only TagusComplaint/test content)"
                )

        if "from" in post:
            print(
                f"📤 From: {post.get('from', {}).get('name', 'Unknown or Private User')}"
            )

        if "created_time" in post:
            print(f"⏰ Created: {post.get('created_time')}")

        # Extract and display media
        media = extract_media_from_post(post)

        # Also try scraping for additional media
        if "permalink_url" in post:
            print("🔍 Searching for additional media...")
            scraped_media = get_media_from_permalink(post.get("permalink_url"))

            # Merge scraped media (avoid duplicates)
            for img in scraped_media["images"]:
                if not any(
                    existing["url"] == img["url"] for existing in media["images"]
                ):
                    media["images"].append(img)

            for vid in scraped_media["videos"]:
                if not any(
                    existing["url"] == vid["url"] for existing in media["videos"]
                ):
                    media["videos"].append(vid)

        total_media = (
            len(media["images"])
            + len(media["videos"])
            + len(media["links"])
            + len(media["other_attachments"])
        )

        if total_media > 0:
            print(f"\n📁 MEDIA CONTENT ({total_media} items):")
            print_media(media)
        else:
            print("\n📁 No media content found")

        print("=" * 80)


# ==================== CONFIGURATION VALIDATOR ====================
def validate_configuration():
    """Validate all configuration"""
    required_vars = {
        "PAGE_ID": "Facebook Page ID",
        "ACCESS_TOKEN": "Facebook Access Token",
        "GROQ_API_KEY": "Groq AI API Key",
    }

    missing = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing.append(f"{var} ({description})")

    if missing:
        print("❌ Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        return False

    # Test Facebook API connection
    try:
        response = requests.get(
            f"https://graph.facebook.com/v23.0/{PAGE_ID}",
            params={"access_token": ACCESS_TOKEN},
        )
        if response.status_code == 200:
            print("✅ Facebook API connection successful")
        else:
            print("❌ Facebook API connection failed")
            return False
    except Exception as e:
        print(f"❌ Facebook API test failed: {e}")
        return False

    # Test Groq API connection
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5,
        )
        print("✅ Groq AI API connection successful")
    except Exception as e:
        print(f"❌ Groq AI API test failed: {e}")
        return False

    print("✅ All configurations validated successfully!")
    return True


# ==================== MAIN ANALYZER ====================
@ErrorHandler().retry_on_failure
def facebook_mentions_complete(
    minutes=None, hours=None, days=None, save_json=True, custom_filename=None
):
    """Complete Facebook mentions analysis with ULTRA-STRICT complaint detection"""

    # Initialize components
    rate_limiter = RateLimiter()
    validator = DataValidator()
    logger = Logger()

    # Validate configuration
    if not validate_configuration():
        raise ValueError("Configuration validation failed")

    # Calculate time range
    current_time = int(time.time())

    if minutes is None and hours is None and days is None:
        days = 30

    total_seconds = 0
    if minutes:
        total_seconds += minutes * 60
    if hours:
        total_seconds += hours * 3600
    if days:
        total_seconds += days * 86400

    since_time = current_time - total_seconds

    # Display search information
    print(f"🚀 FACEBOOK MENTIONS WITH ULTRA-STRICT COMPLAINT ANALYSIS")
    print(f"={'='*80}")
    print(f"🔍 Search Parameters:")
    print(f"   📅 From: {time.ctime(since_time)}")
    print(f"   📅 To: {time.ctime(current_time)}")
    print(f"   ⏱️  Range: {total_seconds/86400:.1f} days")
    print(
        f"   📋 Features: Username extraction, Media detection, STRICT complaint analysis"
    )
    print(
        f"   🚫 Aggressive Filtering: TagusComplaint completely removed, test messages rejected"
    )
    print(
        f"   ⚡ Requirements: Complaints must have detailed descriptions and specific issues"
    )

    # Facebook API parameters - Using your exact specification
    params_common = {
        "access_token": ACCESS_TOKEN,
        "limit": 100,
        "since": since_time,
    }

    tagged_url = f"https://graph.facebook.com/v23.0/{PAGE_ID}/tagged"

    print(f"\n🧪 Using your exact specification:")
    print(f"   URL: {tagged_url}")
    print(f"   Fields: id,message,from,created_time,permalink_url,full_picture,picture")

    # Fetch data from Facebook API
    try:
        tagged_posts = get_paginated_data(
            tagged_url,
            {
                **params_common,
                "fields": "id,message,from,created_time,permalink_url,full_picture,picture",
            },
            rate_limiter,
            logger,
        )

        if tagged_posts:
            print(f"✅ SUCCESS! Found {len(tagged_posts)} posts")
        else:
            print(f"⚠️  No posts found")
            return []

    except Exception as e:
        print(f"❌ API call failed: {str(e)}")
        logger.log_error(e, "Facebook API")
        return []

    # Display results in console
    print_items(tagged_posts, "Tagged Mentions", rate_limiter, validator)

    # Console Summary
    print(f"\n📊 CONSOLE SUMMARY:")
    total_media = 0
    total_complaints = 0

    for post in tagged_posts:
        if not validator.validate_post_data(post):
            continue

        media = extract_media_from_post(post)

        # Add scraped media count
        if "permalink_url" in post:
            scraped_media = get_media_from_permalink(post.get("permalink_url"))
            total_media += (
                len(media["images"])
                + len(media["videos"])
                + len(media["links"])
                + len(media["other_attachments"])
            )
            total_media += len(scraped_media["images"]) + len(scraped_media["videos"])
        else:
            total_media += (
                len(media["images"])
                + len(media["videos"])
                + len(media["links"])
                + len(media["other_attachments"])
            )

        # Count STRICT complaints only
        message = post.get("message", "")
        cleaned_message = validator.aggressive_clean_message_text(message)
        if cleaned_message and is_complaint_ultra_strict(cleaned_message):
            total_complaints += 1

    print(f"✅ Total posts found: {len(tagged_posts)}")
    print(f"📁 Total media items: {total_media}")
    print(f"⚠️  GENUINE complaints (strict validation): {total_complaints}")
    print(
        f"📊 Complaint rate: {(total_complaints/len(tagged_posts)*100):.1f}%"
        if tagged_posts
        else "0%"
    )
    print(f"🎯 Note: Only detailed complaints with specific issues are counted")

    # Save to JSON
    if save_json and tagged_posts:
        print(f"\n💾 SAVING TO JSON...")
        json_data = prepare_data_for_json(tagged_posts, validator, rate_limiter, logger)
        saved_file = save_to_json(json_data, custom_filename)

        if saved_file:
            print(f"\n📊 JSON EXPORT SUMMARY:")
            summary = json_data["summary"]
            print(f"✅ Posts saved: {summary['total_posts']}")
            print(f"📷 Images found: {summary['total_images']}")
            print(f"🎥 Videos found: {summary['total_videos']}")
            print(f"🔗 Links found: {summary['total_links']}")
            print(f"👤 Usernames extracted: {summary['usernames_extracted']}")
            print(f"📁 Posts with media: {summary['posts_with_media']}")
            print(f"⚠️  GENUINE complaints detected: {summary['total_complaints']}")
            print(f"📊 Complaint rate: {summary['complaint_rate']}")

    return tagged_posts


# ==================== UTILITY FUNCTIONS ====================
def load_json_data(filename):
    """Load previously saved JSON data"""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"📂 Loaded data from: {filename}")
        return data
    except Exception as e:
        print(f"❌ Error loading JSON: {str(e)}")
        return None


def print_complaints_only(filename):
    """Print only GENUINE complaints from saved JSON file"""
    data = load_json_data(filename)
    if data and "posts" in data:
        complaints = [
            post for post in data["posts"] if post["complaint"]["is_complaint"]
        ]

        print(f"\n⚠️  GENUINE COMPLAINTS SUMMARY ({len(complaints)} found):")
        print("=" * 60)

        for i, complaint in enumerate(complaints, 1):
            print(f"\n--- GENUINE COMPLAINT #{i} ---")
            print(f"👤 User: {complaint['username']}")
            print(f"💬 Original: {complaint['message'][:150]}...")
            print(f"🧹 Cleaned: {complaint.get('cleaned_message', '')[:150]}...")
            print(f"⏰ Date: {complaint['created_time']}")

            if "analysis" in complaint["complaint"]:
                analysis = complaint["complaint"]["analysis"]
                print(f"🎯 Priority: {analysis.get('priority_score', 'N/A')}/5")
                print(f"🏢 Department: {analysis.get('department', 'N/A')}")
                print(
                    f"👨‍💼 Recommended Officer: {analysis.get('recommended_officer', 'N/A')}"
                )

                if "ai_analysis" in analysis:
                    ai = analysis["ai_analysis"]
                    print(f"😊 Sentiment: {ai.get('sentiment', 'N/A')}")
                    print(f"📊 Category: {ai.get('category', 'N/A')}")
                    print(f"📝 Summary: {ai.get('summary', 'N/A')}")

            print("-" * 50)


def print_json_summary(filename):
    """Print summary from saved JSON file"""
    data = load_json_data(filename)
    if data and "summary" in data:
        print(f"\n📊 SUMMARY FROM {filename}:")
        summary = data["summary"]
        for key, value in summary.items():
            print(f"   {key}: {value}")


# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    print("🚀 ULTRA-STRICT FACEBOOK MENTIONS & COMPLAINT ANALYSIS SYSTEM")
    print("=" * 80)
    print("🎯 FEATURES:")
    print("   • Aggressive TagusComplaint filtering (complete removal)")
    print("   • Ultra-strict complaint detection (requires detailed descriptions)")
    print("   • Pre-filtering eliminates test messages, greetings, simple questions")
    print("   • Only genuine government service complaints are classified")
    print("=" * 80)

    # Run with all features enabled
    posts = facebook_mentions_complete(days=5, hours=0, minutes=15, save_json=True)

    print(f"\n🏁 ANALYSIS COMPLETED!")
    print(f"📊 Total posts processed: {len(posts)}")
    print(f"✨ Only GENUINE detailed complaints classified!")
    print(f"🚫 TagusComplaint mentions completely filtered out!")

    # Show available utility functions
    print(f"\n🛠️  UTILITY FUNCTIONS AVAILABLE:")
    print(f"   📂 load_json_data('filename.json') - Load saved data")
    print(
        f"   ⚠️  print_complaints_only('filename.json') - Show only GENUINE complaints"
    )
    print(f"   📊 print_json_summary('filename.json') - Show file summary")
