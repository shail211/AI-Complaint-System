import time
from datetime import datetime
from config import Config
from error_handler import ErrorHandler
from rate_limiter import RateLimiter
from logger import Logger
from data_validator import DataValidator
from web_scraper import WebScraper
from facebook_api import FacebookAPI
from media_processor import MediaProcessor
from ai_analyzer import AIAnalyzer
from data_processor import DataProcessor
from file_manager import FileManager
from display_manager import DisplayManager


class FacebookMentionsAnalyzer:
    def __init__(self):
        # Initialize all components
        self.error_handler = ErrorHandler()
        self.rate_limiter = RateLimiter()
        self.logger = Logger()
        self.validator = DataValidator()
        self.web_scraper = WebScraper()
        self.media_processor = MediaProcessor()
        self.ai_analyzer = AIAnalyzer(self.rate_limiter)
        self.facebook_api = FacebookAPI(self.rate_limiter, self.logger)
        self.data_processor = DataProcessor(
            self.web_scraper,
            self.media_processor,
            self.ai_analyzer,
            self.validator,
            self.logger,
        )
        self.file_manager = FileManager()
        self.display_manager = DisplayManager()

        # Validate configuration
        if not self._validate_configuration():
            raise ValueError("Configuration validation failed")

    def _validate_configuration(self):
        """Validate all required configuration"""
        required_vars = ["PAGE_ID", "ACCESS_TOKEN", "GROQ_API_KEY"]
        missing = [var for var in required_vars if not getattr(Config, var)]

        if missing:
            print(f"❌ Missing configuration: {', '.join(missing)}")
            return False

        print("✅ Configuration validated successfully!")
        return True

    @ErrorHandler().retry_on_failure
    def analyze_mentions(
        self, minutes=None, hours=None, days=None, save_json=True, custom_filename=None
    ):
        """Main analysis function"""
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
        print(f"🚀 MODULAR FACEBOOK MENTIONS & COMPLAINT ANALYSIS")
        print(f"={'='*80}")
        print(f"🔍 Search Parameters:")
        print(f"   📅 From: {time.ctime(since_time)}")
        print(f"   📅 To: {time.ctime(current_time)}")
        print(f"   ⏱️  Range: {total_seconds/86400:.1f} days")
        print(f"   🚫 Aggressive TagusComplaint filtering enabled")
        print(f"   ⚡ Ultra-strict complaint validation active")

        # Fetch data from Facebook API
        try:
            posts = self.facebook_api.get_tagged_mentions(since_time)

            if not posts:
                print("⚠️  No posts found")
                return []

            print(f"✅ SUCCESS! Found {len(posts)} posts")

        except Exception as e:
            print(f"❌ API call failed: {str(e)}")
            self.logger.log_error(e, "Facebook API")
            return []

        # Process all data
        processed_data = self.data_processor.prepare_data_for_export(posts)

        # Console Summary
        print(f"\n📊 ANALYSIS SUMMARY:")
        summary = processed_data["summary"]
        print(f"✅ Posts processed: {summary['total_posts']}")
        print(f"📷 Images found: {summary['total_images']}")
        print(f"🎥 Videos found: {summary['total_videos']}")
        print(f"⚠️  GENUINE complaints: {summary['total_complaints']}")
        print(f"📊 Complaint rate: {summary['complaint_rate']}")

        # Save to JSON
        if save_json:
            print(f"\n💾 SAVING TO JSON...")
            saved_file = self.file_manager.save_to_json(processed_data, custom_filename)

            if saved_file:
                print(f"✅ Data exported successfully!")
                return processed_data["posts"], saved_file

        return processed_data["posts"], None

    def print_complaints_only(self, filename):
        """Show only complaints from a saved file"""
        self.display_manager.print_complaints_only(filename, self.file_manager)


# Usage Examples
def main():
    try:
        analyzer = FacebookMentionsAnalyzer()

        # Run analysis
        posts, saved_file = analyzer.analyze_mentions(days=5, save_json=True)

        print(f"\n🏁 COMPLETED!")
        print(f"📊 Posts processed: {len(posts)}")

        if saved_file:
            print(f"💾 Data saved to: {saved_file}")

            # Show only complaints
            analyzer.print_complaints_only(saved_file)

    except Exception as e:
        print(f"❌ System error: {e}")


if __name__ == "__main__":
    main()
