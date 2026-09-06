import os
import json
import time
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

def analyze_audit_data(audit_report: dict) -> str:
    """
    Uses Groq AI (qwen/qwen3.8-27b) to convert technical website audit data
    into a high-converting executive summary with rate-limiting controls.
    """
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        raise ValueError("Missing or default GROQ_API_KEY in .env file. Please add your actual API key.")

    client = Groq(api_key=GROQ_API_KEY)
    
    # Token Budget Control: Format JSON and cap payload length to protect the 8K tokens/min limit
    raw_json_data = json.dumps(audit_report, indent=2)
    if len(raw_json_data) > 2000:
        raw_json_data = raw_json_data[:2000] + "\n...[truncated for token efficiency]"

    prompt = f"""
You are an elite B2B Technical Auditor and Web Performance Consultant.
Analyze the following website audit metrics for domain: {audit_report.get('domain')}

Raw Technical Data:
{raw_json_data}

Provide a structured, highly persuasive executive summary in Markdown format with:
1. **Health Score**: Rate the site performance out of 100 based on the metrics.
2. **Business Impact & Flaws**: Explain how any detected errors (slow load, missing title, missing viewport, missing SSL) negatively affect lead conversion and search ranking.
3. **Actionable Fixes**: 3 prioritized technical steps to optimize the domain.

Keep the tone concise, authoritative, and focused on business growth.
"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are a concise B2B web performance and technical audit specialist."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,  # Caps output tokens to protect 8K tokens/min budget
                temperature=0.3
            )
            
            # Pace requests to ensure compliance with 30 requests/minute limit
            time.sleep(2)
            
            return response.choices[0].message.content.strip()

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate_limit" in err_str.lower():
                wait_time = (attempt + 1) * 5
                print(f"  ⚠️ Groq rate limit hit. Pausing for {wait_time}s (Attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
            else:
                raise e

    raise RuntimeError("Failed to generate analysis from Groq after multiple retry attempts due to rate limits.")


if __name__ == "__main__":
    from auditor import audit_website
    
    test_domain = "example.com"
    print(f"Auditing and analyzing target: {test_domain}...")
    audit_results = audit_website(test_domain)
    
    ai_analysis = analyze_audit_data(audit_results)
    
    print("\n--- Groq AI Executive Analysis ---")
    print(ai_analysis)