import os
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup
from db import supabase

# Target geography and niche defaults
DEFAULT_NICHE = "HVAC Contractors"
DEFAULT_CITY = "Lagos"

def normalize_domain(url: str) -> str:
    """Standardizes domain strings for clean database deduplication."""
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc or parsed.path
    domain = domain.lower().replace("www.", "")
    return domain.split("/")[0]

def extract_email_from_url(website_url: str) -> str:
    """
    Fallback Extractor: Scrapes website homepage, /contact, and /about 
    for mailto links and email regex patterns.
    """
    if not website_url.startswith(("http://", "https://")):
        website_url = "https://" + website_url

    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    found_emails = set()
    paths_to_check = ["", "/contact", "/contact-us", "/about", "/about-us"]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    base_domain = normalize_domain(website_url)

    for path in paths_to_check:
        target_url = f"https://{base_domain}{path}"
        try:
            res = requests.get(target_url, headers=headers, timeout=5)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                
                # Check mailto links
                for a in soup.find_all("a", href=True):
                    if a["href"].startswith("mailto:"):
                        email = a["href"].replace("mailto:", "").split("?")[0].strip()
                        if email:
                            found_emails.add(email)

                # Check body text regex
                matches = re.findall(email_regex, res.text)
                for match in matches:
                    # Ignore common asset false positives
                    if not match.endswith((".png", ".jpg", ".jpeg", ".svg", ".webp", ".js", ".css")):
                        found_emails.add(match)

                if found_emails:
                    break
        except Exception:
            continue

    return list(found_emails)[0] if found_emails else ""

def discover_leads(niche: str = DEFAULT_NICHE, city: str = DEFAULT_CITY, max_results: int = 10):
    """
    Main lead discovery function.
    Accepts raw lead dictionaries or integrates with directory APIs/scrapers.
    """
    print(f"🔍 Starting lead discovery for '{niche}' in '{city}'...")

    # Sample lead targets (Replace or feed dynamically via SerpAPI, Outscraper, or Google Maps API)
    raw_leads = [
        {
            "business_name": "Apex HVAC Solutions",
            "website_url": "https://example.com",
            "contact_email": "",
            "niche": niche,
            "city": city
        }
    ]

    discovered_count = 0

    for lead in raw_leads:
        domain = normalize_domain(lead.get("website_url"))
        if not domain:
            continue

        # 1. Deduplication check in Supabase
        existing = supabase.table("leads").select("id").eq("domain", domain).execute()
        if existing.data:
            print(f"⏭️ Skipping {domain} (already in database)")
            continue

        # 2. Fallback Email Extractor if email missing
        email = lead.get("contact_email")
        if not email:
            print(f"🔎 Scraping email fallback for {domain}...")
            email = extract_email_from_url(domain)

        if not email:
            print(f"⚠️ Could not find contact email for {domain}. Skipping...")
            continue

        # 3. Save to Supabase leads table
        try:
            new_lead = supabase.table("leads").insert({
                "domain": domain,
                "business_name": lead.get("business_name", ""),
                "contact_email": email,
                "niche": lead.get("niche", niche),
                "city": lead.get("city", city),
                "status": "DISCOVERED"
            }).execute()

            if new_lead.data:
                discovered_count += 1
                print(f"✅ Logged new lead: {domain} ({email})")
        except Exception as e:
            print(f"❌ Database insert error for {domain}: {str(e)}")

    print(f"\n✨ Discovery run complete. Added {discovered_count} new leads.")
    return discovered_count

if __name__ == "__main__":
    discover_leads()