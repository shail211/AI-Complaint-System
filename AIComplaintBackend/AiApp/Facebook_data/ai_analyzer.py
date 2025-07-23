# ai_analyzer.py (Enhanced Version)
import re
import json
from groq import Groq
from config import Config


class AIAnalyzer:
    def __init__(self, rate_limiter):
        self.client = Groq(api_key=Config.GROQ_API_KEY)
        self.model = Config.MODEL_NAME
        self.rate_limiter = rate_limiter

        # Semantic location patterns
        self.location_patterns = {
            "in": r"\bin\s+([A-Za-z\s]{2,15})(?:\s|,|\.|\b)",
            "at": r"\bat\s+([A-Za-z\s]{2,15})(?:\s|,|\.|\b)",
            "on": r"\bon\s+([A-Za-z\s]{2,15})(?:\s|,|\.|\b)",
            "near": r"\bnear\s+([A-Za-z\s]{2,15})(?:\s|,|\.|\b)",
            "around": r"\baround\s+([A-Za-z\s]{2,15})(?:\s|,|\.|\b)",
            "from": r"\bfrom\s+([A-Za-z\s]{2,15})(?:\s|,|\.|\b)",
        }

    def is_complaint(self, text):
        """Simple semantic complaint detection"""
        if not text or len(text.strip()) < 5:
            return False

        # Quick non-complaint filters
        obvious_non_complaints = [
            r"^\s*(test|testing|hi|hello|hey)\s*$",
            r"^\s*(video|image)\s*\d*\s*$",
            r"where\s+is\s+my\s+post",
        ]

        for pattern in obvious_non_complaints:
            if re.search(pattern, text, re.IGNORECASE):
                return False

        print(f"   🤖 AI complaint analysis...")

        prompt = f"""
Is this a complaint about public services or infrastructure?
Use semantic understanding to identify complaints about:
- Roads, water, electricity, buildings
- Government services, permits, offices
- Public facilities, hospitals, schools

Text: "{text}"
Answer only "true" or "false":
"""

        try:
            self.rate_limiter.wait_if_needed("groq")
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Identify complaints about public services using semantic understanding.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=5,
            )

            response = completion.choices[0].message.content.strip().lower()
            result = response == "true"
            print(f"   🎯 AI decision: {response}")
            return result

        except Exception as e:
            print(f"   ❌ AI error: {e}")
            return False

    def analyze_complaint_with_location(self, complaint_text):
        """Enhanced complaint analysis with semantic location detection"""

        prompt = f"""
Analyze this complaint and extract information including location details:

COMPLAINT: "{complaint_text}"

Look for:
1. Priority (1-5 scale)
2. Relevant department from list below
3. Recommended officer
4. LOCATION extraction using grammar patterns:
   - "in [place]" - incident location
   - "at [place]" - service location  
   - "near [landmark]" - reference point
   - "on [road/street]" - infrastructure location
5. Sentiment and urgency analysis

Departments and Officers:
{Config.DEPARTMENTS_OFFICERS}

Respond with JSON:
{{
  "priority_score": 1-5,
  "department": "department name",
  "recommended_officer": "officer name", 
  "location_analysis": {{
    "primary_location": "main location mentioned",
    "extraction_method": "grammatical pattern used",
    "confidence": 1-100,
    "location_type": "village|town|district|landmark|road",
    "context": "how location was mentioned"
  }},
  "ai_analysis": {{
    "sentiment": "sentiment",
    "urgency_level": "low|medium|high",
    "category": "category",
    "summary": "brief summary",
    "suggested_actions": ["action1", "action2"]
  }}
}}
"""

        try:
            self.rate_limiter.wait_if_needed("groq")
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing complaints and extracting location information using grammatical patterns and semantic context.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=800,
            )

            content = completion.choices[0].message.content.strip()

            try:
                result = json.loads(content)
                return self._enhance_location_data(result, complaint_text)
            except json.JSONDecodeError:
                match = re.search(r"\{[\s\S]*\}", content)
                if match:
                    result = json.loads(match.group())
                    return self._enhance_location_data(result, complaint_text)
                raise

        except Exception as e:
            print(f"   ❌ Analysis error: {e}")
            return None

    def _enhance_location_data(self, ai_result, original_text):
        """Enhance AI location analysis with pattern validation"""

        # Validate location extraction with regex patterns
        location_analysis = ai_result.get("location_analysis", {})
        if location_analysis.get("primary_location"):

            # Cross-validate with regex patterns
            pattern_matches = []
            for pattern_name, regex in self.location_patterns.items():
                matches = re.findall(regex, original_text, re.IGNORECASE)
                if matches:
                    pattern_matches.append(
                        {"pattern": pattern_name, "matches": matches, "validated": True}
                    )

            # Enhance location data
            location_analysis["pattern_validation"] = pattern_matches
            location_analysis["validation_score"] = (
                len(pattern_matches) * 20
            )  # Boost confidence

            print(
                f"   📍 Location: {location_analysis.get('primary_location')} ({location_analysis.get('confidence', 0)}%)"
            )

        return ai_result
