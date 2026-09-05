import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def analyze_audit_data(audit_report: dict) -> str:
    """
    Uses Gemini AI to convert technical website audit data into a high-converting executive summary.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        raise ValueError("Missing or default GEMINI_API_KEY in .env file. Please add your actual API key.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
You are an elite B2B Technical Auditor and Web Performance Consultant.
Analyze the following website audit metrics for domain: {audit_report.get('domain')}

Raw Technical Data:
{json.dumps(audit_report, indent=2)}

Provide a structured, highly persuasive executive summary in Markdown format with:
1. **Health Score**: Rate the site performance out of 100 based on the metrics.
2. **Business Impact & Flaws**: Explain how any detected errors (slow load, missing title, missing viewport, missing SSL) negatively affect lead conversion and search ranking.
3. **Actionable Fixes**: 3 prioritized technical steps to optimize the domain.

Keep the tone concise, authoritative, and focused on business growth.
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )
    
    return response.text

if __name__ == "__main__":
    from auditor import audit_website
    
    test_domain = "example.com"
    print(f"Auditing and analyzing target: {test_domain}...")
    audit_results = audit_website(test_domain)
    
    ai_analysis = analyze_audit_data(audit_results)
    
    print("\n--- Gemini AI Executive Analysis ---")
    print(ai_analysis)