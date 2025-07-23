import logging
import os
from datetime import datetime


class Logger:
    def __init__(self, log_level=logging.INFO):
        self.logger = logging.getLogger("facebook_mentions")
        self.logger.setLevel(log_level)

        # Create logs directory if it doesn't exist
        if not os.path.exists("logs"):
            os.makedirs("logs")

        # File handler - using Tuesday, July 22, 2025 format as preferred
        log_date = datetime.now().strftime("%A_%B_%d_%Y")
        log_filename = f"logs/facebook_mentions_{log_date}.log"
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
