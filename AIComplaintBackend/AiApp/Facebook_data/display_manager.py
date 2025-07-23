class DisplayManager:
    def print_media(self, media):
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

    def print_complaints_only(self, filename, file_manager):
        """Print only GENUINE complaints from saved JSON file"""
        data = file_manager.load_json_data(filename)
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
                    print(f"👨‍💼 Officer: {analysis.get('recommended_officer', 'N/A')}")

                    if "ai_analysis" in analysis:
                        ai = analysis["ai_analysis"]
                        print(f"😊 Sentiment: {ai.get('sentiment', 'N/A')}")
                        print(f"📊 Category: {ai.get('category', 'N/A')}")
                        print(f"📝 Summary: {ai.get('summary', 'N/A')}")

                print("-" * 50)

    # display_manager.py (Add to existing print methods)
    def print_complaint_with_location(self, post_data):
        """Print complaint information including location analysis"""

        complaint = post_data.get("complaint", {})
        if complaint.get("is_complaint") and complaint.get("analysis"):
            analysis = complaint["analysis"]

            # Display complaint details
            print(f"   🎯 Priority: {analysis.get('priority_score', 'N/A')}/5")
            print(f"   🏢 Department: {analysis.get('department', 'N/A')}")
            print(f"   👨‍💼 Officer: {analysis.get('recommended_officer', 'N/A')}")

            # Display location analysis
            location_analysis = analysis.get("location_analysis", {})
            if location_analysis.get("primary_location"):
                print(f"   📍 Location: {location_analysis['primary_location']}")
                print(
                    f"   🔍 Method: {location_analysis.get('extraction_method', 'N/A')}"
                )
                print(f"   ✅ Confidence: {location_analysis.get('confidence', 0)}%")

                # Show pattern validation if available
                pattern_validation = location_analysis.get("pattern_validation", [])
                if pattern_validation:
                    print(f"   🔤 Patterns found:")
                    for pv in pattern_validation[:2]:  # Show top 2
                        print(f"      • '{pv['pattern']}': {pv['matches']}")
