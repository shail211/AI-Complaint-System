import os
from dotenv import load_dotenv
from groq import Groq
import re
import json as pyjson
import traceback

load_dotenv()
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

client = Groq(api_key=GROQ_API_KEY)
MODEL_NAME = 'gemma2-9b-it' # or 'llama2-70b-4096' if you want to use Llama. You can also check GROQ CLOUD for more models.

def analyze_complaint(complaint_text):
    departments_officers = '''
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
'''
    prompt = f"""
Analyze the following complaint and provide:
1. A priority score (1-5, 5 is most urgent)
2. The most relevant department (choose ONLY from the list below)
3. The name of a recommended officer (choose ONLY from the officers listed under the selected department)
4. An AI analysis object with: sentiment, urgency_level, category, summary, and suggested_actions (as a list of strings).

Departments and officers:
{departments_officers}

Complaint: {complaint_text}

Respond ONLY with a valid JSON object with keys: priority_score, department, recommended_officer, ai_analysis. Do NOT include any explanation or markdown.
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an expert complaint triage assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=1,
            max_tokens=1024,
            top_p=1,
            stream=False,
            stop=None,
        )
        content = completion.choices[0].message.content
       
        content = re.sub(r"^```(?:json)?\s*|```$", "", content.strip(), flags=re.IGNORECASE | re.MULTILINE)
        try:
            return pyjson.loads(content)
        except Exception:
            # Fallback: extract first JSON object from the string
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                return pyjson.loads(match.group(0))
            raise
    except Exception as e:
        print(f"Groq AI error: {e}")
        traceback.print_exc()
        return None