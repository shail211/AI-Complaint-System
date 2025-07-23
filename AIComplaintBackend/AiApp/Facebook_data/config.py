import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # API Configuration
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

    # Rate limiting settings
    MAX_REQUESTS_PER_HOUR = 200
    FACEBOOK_DELAY = 0.5
    GROQ_DELAY = 1.0

    # Validation settings
    MIN_COMPLAINT_LENGTH = 2  # Reduced from 15
    MIN_MEANINGFUL_WORDS = 1  # Reduced from 5 - allows "bad road condition"
