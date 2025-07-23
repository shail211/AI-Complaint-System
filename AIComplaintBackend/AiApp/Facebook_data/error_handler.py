import time
from functools import wraps
import requests


class ErrorHandler:
    def __init__(self, max_retries=3, retry_delay=2):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

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
