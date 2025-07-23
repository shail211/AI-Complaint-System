import requests
import time
from config import Config


class FacebookAPI:
    def __init__(self, rate_limiter, logger):
        self.access_token = Config.ACCESS_TOKEN
        self.page_id = Config.PAGE_ID
        self.rate_limiter = rate_limiter
        self.logger = logger

    def get_paginated_data(self, url, params):
        """Get all paginated data from Facebook API with rate limiting"""
        all_data = []
        page_count = 0

        while url and page_count < 10:
            try:
                self.rate_limiter.wait_if_needed("facebook")
                response = requests.get(url, params=params, timeout=30)

                self.logger.log_api_call(f"Page {page_count + 1}", response.status_code)

                if response.status_code != 200:
                    print(
                        f"⚠️  API Error on page {page_count + 1}: {response.status_code}"
                    )
                    break

                data = response.json()

                if "error" in data:
                    print(f"⚠️  Facebook Error: {data['error']}")
                    self.logger.log_error(data["error"], f"Page {page_count + 1}")
                    break

                if "data" in data:
                    all_data.extend(data["data"])
                    print(
                        f"📄 Fetched page {page_count + 1}: {len(data['data'])} posts"
                    )

                url = data.get("paging", {}).get("next")
                params = {}
                page_count += 1

            except Exception as e:
                print(f"❌ Error on page {page_count + 1}: {str(e)}")
                self.logger.log_error(e, f"Page {page_count + 1}")
                break

        return all_data

    def get_tagged_mentions(self, since_time):
        """Get tagged mentions from Facebook"""
        params_common = {
            "access_token": self.access_token,
            "limit": 100,
            "since": since_time,
        }

        tagged_url = f"https://graph.facebook.com/v23.0/{self.page_id}/tagged"

        return self.get_paginated_data(
            tagged_url,
            {
                **params_common,
                "fields": "id,message,from,created_time,permalink_url,full_picture,picture",
            },
        )
