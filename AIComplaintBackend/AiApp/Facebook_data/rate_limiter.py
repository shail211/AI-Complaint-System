import time
from datetime import datetime, timedelta
from config import Config


class RateLimiter:
    def __init__(self):
        self.max_requests = Config.MAX_REQUESTS_PER_HOUR
        self.requests = []
        self.facebook_delay = Config.FACEBOOK_DELAY
        self.groq_delay = Config.GROQ_DELAY

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
