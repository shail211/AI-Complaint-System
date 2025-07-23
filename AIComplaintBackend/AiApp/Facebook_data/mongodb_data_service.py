# mongodb_data_service.py - Enhanced with comprehensive statistics
import os
from pymongo import MongoClient
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


class MongoDBComplaintService:
    def __init__(self):
        self.connection_string = os.getenv("MONGODB_URI")
        self.client = None
        self.db = None
        self.complaints_collection = None
        self.connect()

    def connect(self):
        """Connect to MongoDB and setup complaints collection only"""
        try:
            self.client = MongoClient(self.connection_string)
            self.client.server_info()
            print("✅ Successfully connected to MongoDB!")

            self.db = self.client["complaint_database"]

            # Setup only complaints collection
            if "complaints" not in self.db.list_collection_names():
                self.db.create_collection("complaints")
                print("📄 Collection 'complaints' created")

            self.complaints_collection = self.db["complaints"]

            # Create unique index to prevent duplicates
            self.setup_unique_index()

        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {str(e)}")
            raise

    def setup_unique_index(self):
        """Create unique index on facebook_post_id for complaints"""
        try:
            self.complaints_collection.create_index(
                "facebook_post_id", unique=True, background=True
            )
            print("✅ Unique index created for complaints collection")
        except Exception as e:
            print(f"⚠️  Index creation note: {e}")

    def save_complaints_only(self, processed_posts):
        """Save ONLY complaints to MongoDB - ignore non-complaints"""
        complaints_saved = 0
        complaints_updated = 0
        non_complaints_skipped = 0

        for post_data in processed_posts:
            try:
                # Only process complaints
                if post_data["complaint"]["is_complaint"]:
                    facebook_post_id = post_data.get("post_id")
                    if not facebook_post_id:
                        print(f"   ⚠️  Skipping complaint without ID")
                        continue

                    complaint_doc = self._map_to_complaint_schema(post_data)

                    # UPSERT complaint (prevent duplicates)
                    result = self.complaints_collection.replace_one(
                        {"facebook_post_id": facebook_post_id},
                        complaint_doc,
                        upsert=True,
                    )

                    if result.upserted_id:
                        complaints_saved += 1
                        print(f"   💾 NEW complaint saved: {facebook_post_id}")
                    elif result.modified_count > 0:
                        complaints_updated += 1
                        print(f"   🔄 Complaint UPDATED: {facebook_post_id}")
                    else:
                        print(f"   ✅ Complaint unchanged: {facebook_post_id}")
                else:
                    # Skip non-complaints
                    non_complaints_skipped += 1

            except Exception as e:
                print(
                    f"   ❌ Error saving complaint {post_data.get('post_id', 'Unknown')}: {e}"
                )

        print(f"\n📊 MONGODB SAVE SUMMARY (Complaints Only):")
        print(f"   ⚠️  Complaints saved: {complaints_saved}")
        print(f"   🔄 Complaints updated: {complaints_updated}")
        print(f"   🚫 Non-complaints skipped: {non_complaints_skipped}")

        return complaints_saved, complaints_updated

    def get_complaints_count(self):
        """Get total complaints in database"""
        return self.complaints_collection.count_documents({})

    def get_comprehensive_stats(self):
        """Get comprehensive statistics for dashboard - FIXED METHOD"""
        try:
            # Get all complaints
            all_complaints = list(self.complaints_collection.find())
            total_count = len(all_complaints)

            if total_count == 0:
                return {
                    "total_complaints": 0,
                    "priority_distribution": [],
                    "department_distribution": [],
                }

            # Priority distribution
            priority_dist = {}
            for complaint in all_complaints:
                priority = complaint.get("priority_score", 1)
                priority_dist[priority] = priority_dist.get(priority, 0) + 1

            priority_distribution = [
                {"_id": k, "count": v} for k, v in sorted(priority_dist.items())
            ]

            # Department distribution
            dept_dist = {}
            for complaint in all_complaints:
                dept = complaint.get("department", "Unknown")
                if dept != "Unknown":
                    dept_dist[dept] = dept_dist.get(dept, 0) + 1

            department_distribution = [
                {"_id": k, "count": v}
                for k, v in sorted(dept_dist.items(), key=lambda x: x[1], reverse=True)
            ]

            return {
                "total_complaints": total_count,
                "priority_distribution": priority_distribution,
                "department_distribution": department_distribution,
            }

        except Exception as e:
            print(f"Error getting comprehensive stats: {e}")
            return {
                "total_complaints": 0,
                "priority_distribution": [],
                "department_distribution": [],
            }

    def get_recent_complaints(self, days=7):
        """Get recent complaints"""
        try:
            # Calculate date threshold
            threshold_date = (datetime.now() - timedelta(days=days)).strftime(
                "%Y-%m-%d"
            )

            # Query recent complaints
            recent_complaints = list(
                self.complaints_collection.find({"date": {"$gte": threshold_date}})
                .sort("priority_score", -1)
                .limit(10)
            )

            return recent_complaints

        except Exception as e:
            print(f"Error getting recent complaints: {e}")
            return []

    def _map_to_complaint_schema(self, post_data):
        """Map complaint data to MongoDB schema"""

        # Parse Facebook creation time
        fb_created_time = post_data.get("created_time", "")
        if fb_created_time:
            try:
                dt = datetime.fromisoformat(fb_created_time.replace("Z", "+00:00"))
                time_str = dt.strftime("%H:%M:%S")
                date_str = dt.strftime("%Y-%m-%d")
            except:
                now = datetime.now()
                time_str = now.strftime("%H:%M:%S")
                date_str = now.strftime("%Y-%m-%d")
        else:
            now = datetime.now()
            time_str = now.strftime("%H:%M:%S")
            date_str = now.strftime("%Y-%m-%d")

        # Extract media links
        media = post_data.get("media", {})
        image_link = media["images"][0].get("url", "") if media.get("images") else ""
        video_link = media["videos"][0].get("url", "") if media.get("videos") else ""

        # Get complaint analysis
        analysis = post_data.get("complaint", {}).get("analysis", {})
        ai_analysis = analysis.get("ai_analysis", {})

        # Enhanced complaint schema
        complaint_doc = {
            "time": time_str,
            "date": date_str,
            "profile_name": post_data.get("username", "Unknown"),
            "image_link": image_link,
            "video_link": video_link,
            "complaint_query": post_data.get(
                "cleaned_message", post_data.get("message", "")
            ),
            "priority_score": analysis.get("priority_score", 1),
            "department": analysis.get("department", "Unknown"),
            "recommended_officer": analysis.get("recommended_officer", "Unknown"),
            "ai_analysis": {
                "sentiment": ai_analysis.get("sentiment", "neutral"),
                "urgency_level": ai_analysis.get("urgency_level", "low"),
                "category": ai_analysis.get("category", "general"),
                "summary": ai_analysis.get("summary", ""),
                "suggested_actions": ai_analysis.get("suggested_actions", []),
            },
            "status": "pending_review",
            # Enhanced metadata
            "facebook_post_id": post_data.get("post_id"),
            "facebook_permalink": post_data.get("permalink_url"),
            "location_data": post_data.get("location_data"),
            "confidence_score": post_data.get("complaint", {}).get(
                "confidence_score", 0
            ),
            "processing_timestamp": datetime.now().strftime(
                "%A, %B %d, %Y at %I:%M %p IST"
            ),
            "last_updated": datetime.now().isoformat(),
        }

        return complaint_doc
