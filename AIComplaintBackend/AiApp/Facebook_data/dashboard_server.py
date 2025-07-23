# dashboard_server.py - Complete MongoDB Dashboard Server
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse as urlparse
from mongodb_data_service import MongoDBComplaintService
from datetime import datetime, timedelta
import traceback


class ComprehensiveDashboardHandler(BaseHTTPRequestHandler):
    mongodb_service = MongoDBComplaintService()

    def do_GET(self):
        # Enable CORS for browser access
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

        # Parse URL and parameters
        parsed_path = urlparse.urlparse(self.path)
        query_params = urlparse.parse_qs(parsed_path.query)

        try:
            if parsed_path.path == "/api/complaints":
                response = self.get_enhanced_complaints(query_params)
            elif parsed_path.path == "/api/stats":
                response = self.get_comprehensive_stats()
            elif parsed_path.path == "/api/departments":
                response = self.get_departments_list()
            elif parsed_path.path == "/api/locations":
                response = self.get_locations_summary()
            elif parsed_path.path == "/health":
                response = {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                response = {
                    "error": "Endpoint not found",
                    "available_endpoints": [
                        "/api/complaints",
                        "/api/stats",
                        "/api/departments",
                        "/api/locations",
                        "/health",
                    ],
                }

            self.wfile.write(json.dumps(response, default=str).encode())

        except Exception as e:
            print(f"❌ API Error: {e}")
            traceback.print_exc()
            error_response = {
                "error": str(e),
                "type": "server_error",
                "timestamp": datetime.now().strftime("%A, %B %d, %Y at %I:%M %p IST"),
            }
            self.wfile.write(json.dumps(error_response).encode())

    def do_OPTIONS(self):
        # Handle CORS preflight requests
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def get_enhanced_complaints(self, query_params):
        """Get enhanced complaints with all government-useful parameters"""
        try:
            print(f"🔍 Processing complaints request: {dict(query_params)}")

            # Build MongoDB query
            query = {}

            # Status filter
            if "status" in query_params and query_params["status"][0]:
                status = query_params["status"][0]
                query["status"] = status

            # Department filter
            if "department" in query_params and query_params["department"][0]:
                query["department"] = query_params["department"][0]

            # Priority filter
            if "priority" in query_params and query_params["priority"][0]:
                query["priority_score"] = int(query_params["priority"][0])

            # Urgency filter
            if "urgency" in query_params and query_params["urgency"][0]:
                query["ai_analysis.urgency_level"] = query_params["urgency"][0]

            # Location filter
            if "location" in query_params and query_params["location"][0]:
                location_filter = query_params["location"][0]
                if location_filter == "identified":
                    query["location_data"] = {"$exists": True, "$ne": None}
                elif location_filter == "unidentified":
                    query["$or"] = [
                        {"location_data": {"$exists": False}},
                        {"location_data": None},
                        {"location_data.location": {"$in": ["", "area", None]}},
                    ]

            # Time filter
            if "timeFilter" in query_params and query_params["timeFilter"][0]:
                time_filter = query_params["timeFilter"][0]
                now = datetime.now()

                if time_filter == "today":
                    query["date"] = now.strftime("%Y-%m-%d")
                elif time_filter == "week":
                    week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
                    query["date"] = {"$gte": week_ago}
                elif time_filter == "month":
                    month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")
                    query["date"] = {"$gte": month_ago}

            print(f"📊 MongoDB query: {query}")

            # Get complaints from MongoDB
            complaints = list(self.mongodb_service.complaints_collection.find(query))
            print(f"✅ Found {len(complaints)} complaints")

            # Format complaints for government dashboard
            formatted_complaints = []
            for complaint in complaints:
                formatted_complaint = self._format_government_complaint(complaint)
                formatted_complaints.append(formatted_complaint)

            # Sort by priority and urgency
            formatted_complaints.sort(
                key=lambda x: (
                    -x.get("priority_score", 0),
                    self._get_urgency_weight(x.get("urgency_level", "low")),
                    x.get("timestamp", ""),
                ),
                reverse=True,
            )

            print(f"🎯 Returning {len(formatted_complaints)} formatted complaints")
            return formatted_complaints

        except Exception as e:
            print(f"❌ Error getting complaints: {e}")
            traceback.print_exc()
            return []

    def _format_government_complaint(self, complaint):
        """Format complaint with all parameters for government action"""

        # Parse timestamp for your preferred date format
        try:
            if complaint.get("date") and complaint.get("time"):
                dt = datetime.strptime(
                    f"{complaint['date']} {complaint['time']}", "%Y-%m-%d %H:%M:%S"
                )
                timestamp = dt.isoformat()
                # Your preferred format: "Wednesday, July 23, 2025 at 12:31 AM IST"
                formatted_datetime = dt.strftime("%A, %B %d, %Y at %I:%M %p IST")
                date_only = dt.strftime("%A, %B %d, %Y")
                time_only = dt.strftime("%I:%M %p IST")
            else:
                dt = datetime.now()
                timestamp = dt.isoformat()
                formatted_datetime = complaint.get(
                    "processing_timestamp", "Unknown time"
                )
                date_only = dt.strftime("%A, %B %d, %Y")
                time_only = dt.strftime("%I:%M %p IST")
        except Exception as e:
            print(f"⚠️  Date parsing error: {e}")
            dt = datetime.now()
            timestamp = dt.isoformat()
            formatted_datetime = "Invalid date format"
            date_only = "Unknown date"
            time_only = "Unknown time"

        # Extract AI analysis data
        ai_analysis = complaint.get("ai_analysis", {})
        location_data = complaint.get("location_data", {})

        # Media links
        facebook_link = complaint.get("facebook_permalink", "")
        image_link = complaint.get("image_link", "")
        video_link = complaint.get("video_link", "")

        # Location information
        location_info = {
            "location": location_data.get("location", "Not identified"),
            "type": location_data.get("type", "Unknown"),
            "confidence": location_data.get("confidence", 0),
            "method": location_data.get("method", "Not specified"),
            "is_identified": bool(
                location_data.get("location")
                and location_data.get("location") != "area"
            ),
        }

        # Government action requirements
        suggested_actions = ai_analysis.get("suggested_actions", [])
        requires_immediate_action = (
            complaint.get("priority_score", 1) >= 4
            or ai_analysis.get("urgency_level") == "high"
        )

        # Enhanced complaint object
        return {
            # Basic identification
            "id": complaint.get(
                "facebook_post_id", str(complaint.get("_id", "unknown"))
            ),
            "mongodb_id": str(complaint.get("_id", "")),
            # Citizen information
            "name": complaint.get("profile_name", "Unknown"),
            "profile_name": complaint.get("profile_name", "Unknown"),
            # Complaint content
            "description": complaint.get("complaint_query", "No description"),
            "complaint_query": complaint.get("complaint_query", "No description"),
            "original_message": complaint.get("original_message", ""),
            # Time information (your preferred format)
            "timestamp": timestamp,
            "createdAt": formatted_datetime,
            "formatted_datetime": formatted_datetime,
            "date_only": date_only,
            "time_only": time_only,
            "processing_time": complaint.get("processing_timestamp", ""),
            "last_updated": complaint.get("last_updated", ""),
            # Priority and urgency
            "priority_score": complaint.get("priority_score", 1),
            "urgency_level": ai_analysis.get("urgency_level", "low"),
            "urgency_weight": self._get_urgency_weight(
                ai_analysis.get("urgency_level", "low")
            ),
            # Department assignment
            "department": complaint.get("department", "Not assigned"),
            "recommended_officer": complaint.get(
                "recommended_officer", "To be assigned"
            ),
            # Status tracking
            "status": complaint.get("status", "pending_review"),
            "status_display": self._format_status_display(
                complaint.get("status", "pending_review")
            ),
            # AI Analysis results
            "sentiment": ai_analysis.get("sentiment", "neutral"),
            "category": ai_analysis.get("category", "general"),
            "summary": ai_analysis.get("summary", "No summary available"),
            "suggested_actions": suggested_actions,
            "action_priority": len(suggested_actions) > 0,
            # Location analysis
            "location_data": location_info,
            "location": location_info["location"],
            "location_confidence": location_info["confidence"],
            "location_identified": location_info["is_identified"],
            # Media links
            "facebook_link": facebook_link,
            "image_link": image_link,
            "video_link": video_link,
            "has_media": bool(image_link or video_link),
            # Government action metadata
            "requires_immediate_action": requires_immediate_action,
            "has_location": location_info["is_identified"],
            "has_officer_assigned": bool(
                complaint.get("recommended_officer")
                and complaint.get("recommended_officer") != "To be assigned"
            ),
            "days_since_reported": (datetime.now() - dt).days if dt else 0,
            # Source tracking
            "source": "mongodb",
            "data_source": "Facebook API Analysis",
            "analysis_method": "AI-powered social media monitoring",
        }

    def _get_urgency_weight(self, urgency_level):
        """Convert urgency to numeric weight for sorting"""
        weights = {"high": 3, "medium": 2, "low": 1, "": 0}
        return weights.get(urgency_level.lower(), 0)

    def _format_status_display(self, status):
        """Format status for display"""
        status_map = {
            "pending_review": "Pending Review",
            "in_progress": "In Progress",
            "resolved": "Resolved",
            "rejected": "Rejected",
        }
        return status_map.get(status, status.title())

    def get_comprehensive_stats(self):
        """Get comprehensive statistics for dashboard"""
        try:
            print("📊 Generating comprehensive statistics...")

            all_complaints = list(self.mongodb_service.complaints_collection.find())
            total_count = len(all_complaints)

            if total_count == 0:
                return self._empty_stats()

            # Initialize counters
            status_counts = {
                "pending_review": 0,
                "in_progress": 0,
                "resolved": 0,
                "rejected": 0,
            }
            priority_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            dept_dist = {}
            urgency_dist = {"high": 0, "medium": 0, "low": 0}
            location_detected = 0
            critical_count = 0

            # Process each complaint
            for complaint in all_complaints:
                # Status distribution
                status = complaint.get("status", "pending_review")
                if status in status_counts:
                    status_counts[status] += 1

                # Priority distribution
                priority = complaint.get("priority_score", 1)
                if priority in priority_dist:
                    priority_dist[priority] += 1
                if priority >= 5:
                    critical_count += 1

                # Department distribution
                dept = complaint.get("department", "Unknown")
                if dept and dept != "Unknown":
                    dept_dist[dept] = dept_dist.get(dept, 0) + 1

                # Urgency distribution
                urgency = complaint.get("ai_analysis", {}).get("urgency_level", "low")
                if urgency in urgency_dist:
                    urgency_dist[urgency] += 1

                # Location detection
                location_data = complaint.get("location_data", {})
                if location_data.get("location") and location_data.get(
                    "location"
                ) not in ["", "area", None]:
                    location_detected += 1

            # Format distributions
            priority_distribution = [
                {
                    "priority": k,
                    "count": v,
                    "percentage": round((v / total_count) * 100, 1),
                }
                for k, v in priority_dist.items()
                if v > 0
            ]

            department_distribution = [
                {
                    "department": k,
                    "count": v,
                    "percentage": round((v / total_count) * 100, 1),
                }
                for k, v in sorted(dept_dist.items(), key=lambda x: x[1], reverse=True)
            ]

            urgency_distribution = [
                {
                    "urgency": k,
                    "count": v,
                    "percentage": round((v / total_count) * 100, 1),
                }
                for k, v in urgency_dist.items()
                if v > 0
            ]

            # Calculate trends
            daily_trend = self._calculate_daily_trend(all_complaints)

            stats = {
                "total": total_count,
                "critical": critical_count,
                "pending": status_counts["pending_review"],
                "inProgress": status_counts["in_progress"],
                "resolved": status_counts["resolved"],
                "rejected": status_counts["rejected"],
                "locationDetected": location_detected,
                "priority_distribution": priority_distribution,
                "department_distribution": department_distribution,
                "urgency_distribution": urgency_distribution,
                "daily_trend": daily_trend,
                "location_coverage": round((location_detected / total_count) * 100, 1),
                "last_updated": datetime.now().strftime(
                    "%A, %B %d, %Y at %I:%M %p IST"
                ),
            }

            print(f"✅ Generated stats for {total_count} complaints")
            return stats

        except Exception as e:
            print(f"❌ Error generating stats: {e}")
            traceback.print_exc()
            return self._empty_stats()

    def _empty_stats(self):
        """Return empty stats structure"""
        return {
            "total": 0,
            "critical": 0,
            "pending": 0,
            "inProgress": 0,
            "resolved": 0,
            "rejected": 0,
            "locationDetected": 0,
            "priority_distribution": [],
            "department_distribution": [],
            "urgency_distribution": [],
            "daily_trend": [],
            "location_coverage": 0,
            "last_updated": datetime.now().strftime("%A, %B %d, %Y at %I:%M %p IST"),
        }

    def _calculate_daily_trend(self, complaints):
        """Calculate daily complaint trend for last 7 days"""
        try:
            daily_counts = {}
            for complaint in complaints:
                date_str = complaint.get("date", "")
                if date_str:
                    daily_counts[date_str] = daily_counts.get(date_str, 0) + 1

            trend = []
            for i in range(6, -1, -1):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                count = daily_counts.get(date, 0)
                trend.append(
                    {
                        "date": date,
                        "count": count,
                        "day": (datetime.now() - timedelta(days=i)).strftime("%A"),
                    }
                )

            return trend
        except:
            return []

    def get_departments_list(self):
        """Get list of departments for filtering"""
        try:
            departments = self.mongodb_service.complaints_collection.distinct(
                "department"
            )
            return [dept for dept in departments if dept and dept != "Unknown"]
        except Exception as e:
            print(f"Error getting departments: {e}")
            return []

    def get_locations_summary(self):
        """Get summary of detected locations"""
        try:
            pipeline = [
                {"$match": {"location_data.location": {"$exists": True, "$ne": None}}},
                {
                    "$group": {
                        "_id": "$location_data.location",
                        "count": {"$sum": 1},
                        "avg_confidence": {"$avg": "$location_data.confidence"},
                    }
                },
                {"$sort": {"count": -1}},
                {"$limit": 20},
            ]

            locations = list(
                self.mongodb_service.complaints_collection.aggregate(pipeline)
            )
            return locations
        except Exception as e:
            print(f"Error getting locations: {e}")
            return []


if __name__ == "__main__":
    print("🚀 Starting MongoDB Complaint Dashboard Server...")
    print("📊 Government Dashboard with AI Analysis & Location Detection")
    print("🔗 Server URL: http://localhost:8000")
    print("📱 Connect your dashboard HTML to this server")
    print("🎯 Optimized for weekday, month name date formatting")
    print()

    try:
        server = HTTPServer(("localhost", 8000), ComprehensiveDashboardHandler)
        print("✅ Server initialized successfully")
        print("📡 Available endpoints:")
        print("   • /api/complaints - Enhanced complaint data")
        print("   • /api/stats - Comprehensive statistics")
        print("   • /api/departments - Department list")
        print("   • /api/locations - Location summary")
        print("   • /health - Server health check")
        print()
        print("🔄 Server ready for connections...")

        server.serve_forever()

    except KeyboardInterrupt:
        print("\n👋 Dashboard server stopped")
    except Exception as e:
        print(f"❌ Server error: {e}")
        traceback.print_exc()
