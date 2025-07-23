# data_processor.py - Enhanced with MongoDB support
from datetime import datetime
from config import Config
from mongodb_data_service import MongoDBComplaintService


class DataProcessor:
    def __init__(self, web_scraper, media_processor, ai_analyzer, validator, logger):
        self.web_scraper = web_scraper
        self.media_processor = media_processor
        self.ai_analyzer = ai_analyzer
        self.validator = validator
        self.logger = logger
        self.mongodb_service = MongoDBComplaintService()  # MongoDB integration

    def process_single_post(self, post):
        """Process single post with enhanced location analysis"""

        if not self.validator.validate_post_data(post):
            return None

        # Extract username using existing method
        username = "Unknown"
        if "permalink_url" in post:
            username = self.web_scraper.get_user_name(post.get("permalink_url"))

        # Extract media
        media = self.media_processor.extract_media_from_post(post)
        if "permalink_url" in post:
            scraped_media = self.web_scraper.get_media_from_permalink(
                post.get("permalink_url")
            )
            media = self.media_processor.merge_scraped_media(media, scraped_media)

        media = self.validator.validate_media_urls(media)
        media_count = self.media_processor.count_media_items(media)

        # Enhanced complaint analysis with location
        message = post.get("message", "")
        cleaned_message = self.validator.aggressive_clean_message_text(message)
        complaint_info = {"is_complaint": False}

        if cleaned_message and cleaned_message.strip():
            print(f"   🔍 Enhanced complaint analysis: '{cleaned_message[:50]}...'")

            if self.ai_analyzer.is_complaint(cleaned_message):
                print(f"   ⚠️  Complaint confirmed! Analyzing details...")
                complaint_info["is_complaint"] = True

                # Use enhanced analysis method
                analysis_result = self.ai_analyzer.analyze_complaint_with_location(
                    cleaned_message
                )

                if analysis_result:
                    complaint_info["analysis"] = analysis_result
                    priority = analysis_result.get("priority_score", "N/A")
                    location = analysis_result.get("location_analysis", {}).get(
                        "primary_location", "No location"
                    )

                    print(
                        f"   ✅ Analysis complete - Priority: {priority}, Location: {location}"
                    )
                    self.logger.log_complaint_analysis(post.get("id"), True, priority)
                else:
                    print(f"   ❌ Failed to analyze complaint details")
            else:
                print(f"   ℹ️  Not a complaint")
                self.logger.log_complaint_analysis(post.get("id"), False)

        # Build enhanced post data
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
            "location_data": self._extract_location_summary(complaint_info),
            "raw_data": {
                "full_picture": post.get("full_picture", ""),
                "picture": post.get("picture", ""),
            },
        }

        return post_data

    def _extract_location_summary(self, complaint_info):
        """Extract location summary for easy access"""
        if not complaint_info.get("is_complaint") or not complaint_info.get("analysis"):
            return None

        location_analysis = complaint_info["analysis"].get("location_analysis", {})
        if location_analysis.get("primary_location"):
            return {
                "location": location_analysis.get("primary_location"),
                "confidence": location_analysis.get("confidence", 0),
                "type": location_analysis.get("location_type", "unknown"),
                "method": location_analysis.get("extraction_method", "unknown"),
            }
        return None

    # In data_processor.py - update the MongoDB method name
    def prepare_complaints_for_mongodb(self, posts):
        """Process posts and save ONLY complaints to MongoDB"""

        print("🔄 Processing posts - saving only complaints to MongoDB...")

        processed_posts = []
        for i, post in enumerate(posts, 1):
            print(f"Processing post {i}/{len(posts)}...")
            processed_post = self.process_single_post(post)
            if processed_post:
                processed_posts.append(processed_post)

        # Save only complaints using updated method
        complaints_saved, complaints_updated = (
            self.mongodb_service.save_complaints_only(processed_posts)
        )

        return processed_posts, complaints_saved, complaints_updated

    def split_and_prepare_data(self, posts):
        """Split posts into complaints and non-complaints with separate summaries"""

        # Process all posts first
        all_processed = []
        for i, post in enumerate(posts, 1):
            print(f"Processing post {i}/{len(posts)}...")
            processed_post = self.process_single_post(post)
            if processed_post:
                all_processed.append(processed_post)

        # Split into two groups
        complaints = [
            post for post in all_processed if post["complaint"]["is_complaint"]
        ]
        non_complaints = [
            post for post in all_processed if not post["complaint"]["is_complaint"]
        ]

        # Create separate data structures
        base_info = {
            "timestamp": datetime.now().isoformat(),
            "page_id": Config.PAGE_ID,
            "export_date": datetime.now().strftime("%A, %B %d, %Y at %I:%M %p IST"),
        }

        complaints_data = {
            "export_info": {
                **base_info,
                "type": "genuine_complaints",
                "total_posts": len(complaints),
            },
            "posts": complaints,
            "summary": self._generate_summary(complaints, "complaints"),
        }

        non_complaints_data = {
            "export_info": {
                **base_info,
                "type": "non_complaints",
                "total_posts": len(non_complaints),
            },
            "posts": non_complaints,
            "summary": self._generate_summary(non_complaints, "non_complaints"),
        }

        return complaints_data, non_complaints_data

    def _generate_summary(self, posts, data_type):
        """Generate summary with correct field names"""
        total_images = sum(len(post["media"]["images"]) for post in posts)
        total_videos = sum(len(post["media"]["videos"]) for post in posts)
        total_links = sum(len(post["media"]["links"]) for post in posts)

        # Count complaints correctly
        total_complaints = sum(1 for post in posts if post["complaint"]["is_complaint"])

        # Count posts with location data
        posts_with_location = sum(1 for post in posts if post.get("location_data"))

        return {
            "data_type": data_type,
            "total_posts": len(posts),
            "total_complaints": total_complaints,
            "total_images": total_images,
            "total_videos": total_videos,
            "total_links": total_links,
            "total_media_items": total_images + total_videos + total_links,
            "posts_with_media": sum(
                1 for post in posts if post["media_count"]["total"] > 0
            ),
            "posts_with_location": posts_with_location,
            "usernames_extracted": sum(
                1
                for post in posts
                if post["username"]
                not in ["Unknown", "Name not found", "Error extracting name"]
            ),
            "complaint_rate": (
                f"{(total_complaints/len(posts)*100):.1f}%" if posts else "0%"
            ),
        }
