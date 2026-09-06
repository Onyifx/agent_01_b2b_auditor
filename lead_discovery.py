import os
import re
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from db import supabase

# Live Render API configuration
RENDER_API_URL = os.getenv("RENDER_API_URL", "https://agent-01-b2b-auditor.onrender.com").rstrip("/")

# Global Target Parameters
TARGET_NICHES = [
    "HVAC Contractors",
    "Digital Marketing Agencies",
    "B2B SaaS Companies",
    "Solar Energy Installers",
    "Commercial Plumbing Services",
    "IT Managed Service Providers"
]

TARGET_CITIES = [
    # North America
    "New York", "Los Angeles", "Chicago", "Toronto",
    # Europe
    "London", "Berlin", "Paris", "Amsterdam",
    # Asia-Pacific
    "Singapore", "Sydney", "Tokyo",
    # Middle East & Africa
    "Dubai", "Riyadh", "Lagos", "Johannesburg"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

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

def trigger_remote_audit(domain: str, contact_email: str, business_name: str = "", niche: str = "", city: str = ""):
    """Pings the live Render FastAPI endpoint to queue an automated audit, PDF report, and email pitch."""
    endpoint = f"{RENDER_API_URL}/audit"
    payload = {
        "domain": domain,
        "contact_email": contact_email,
        "business_name": business_name,
        "niche": niche,
        "city": city
    }
    try:
        res = requests.post(endpoint, json=payload, timeout=10)
        if res.status_code == 200:
            print(f"  🚀 Queued live Render audit for {domain}")
        else:
            print(f"  ⚠️ Failed to queue remote audit for {domain} (HTTP {res.status_code}): {res.text}")
    except Exception as e:
        print(f"  ❌ Error triggering remote audit for {domain}: {str(e)}")

def search_web_leads(niche: str, city: str, max_results: int = 3) -> list:
    """Queries DuckDuckGo via DDGS client to retrieve target business URLs."""
    query = f"{niche} in {city}"
    found_urls = []
    ignored_domains = [
        "duckduckgo.com", "google.com", "bing.com", "facebook.com",
        "linkedin.com", "instagram.com", "yelp.com", "yellowpages.com",
        "wikipedia.org", "clutch.co", "tripadvisor.com"
    ]

    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results * 3)
            if results:
                for r in results:
                    raw_href = r.get("href", "")
                    domain = normalize_domain(raw_href)
                    if domain and not any(ignored in domain for ignored in ignored_domains):
                        found_urls.append((domain, f"https://{domain}"))
                        if len(found_urls) >= max_results:
                            break
    except Exception as e:
        print(f"  ⚠️ Search notice for '{query}': {str(e)}")

    return found_urls

def extract_email_from_url(website_url: str) -> str:
    """Scrapes website homepage, /contact, and /about for mailto links and email regex patterns."""
    if not website_url.startswith(("http://", "https://")):
        website_url = "https://" + website_url

    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    found_emails = set()
    paths_to_check = ["", "/contact", "/contact-us", "/about", "/about-us"]

    base_domain = normalize_domain(website_url)

    for path in paths_to_check:
        target_url = f"https://{base_domain}{path}"
        try:
            res = requests.get(target_url, headers=HEADERS, timeout=5)
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
                    if not match.endswith((".png", ".jpg", ".jpeg", ".svg", ".webp", ".js", ".css")):
                        found_emails.add(match)

                if found_emails:
                    break
        except Exception:
            continue

    return list(found_emails)[0] if found_emails else ""

def discover_leads_for_target(niche: str, city: str):
    """Discovers live leads dynamically for a given niche and city and queues audits on Render."""
    print(f"\n🔍 Searching live web: '{niche}' in '{city}'...")

    live_targets = search_web_leads(niche, city, max_results=3)
    if not live_targets:
        print(f"  ℹ️ No direct domain targets found for {niche} in {city}.")
        return 0

    discovered_count = 0

    for domain, website_url in live_targets:
        # 1. Deduplication check in Supabase
        existing = supabase.table("leads").select("id").eq("domain", domain).execute()
        if existing.data:
            print(f"  ⏭️ Skipping {domain} (already in database)")
            continue

        # 2. Extract email dynamically
        print(f"  🔎 Scraping contact email for {domain}...")
        email = extract_email_from_url(website_url)

        if not email:
            print(f"  ⚠️ Could not find contact email for {domain}. Skipping...")
            continue

        # 3. Save lead to Supabase
        try:
            business_name = domain.split(".")[0].replace("-", " ").title()
            new_lead = supabase.table("leads").insert({
                "domain": domain,
                "business_name": business_name,
                "contact_email": email,
                "niche": niche,
                "city": city,
                "status": "DISCOVERED"
            }).execute()

            if new_lead.data:
                discovered_count += 1
                print(f"  ✅ Logged new lead: {domain} ({email}) [{city}]")
                
                # 4. Immediately trigger audit pipeline via live Render endpoint
                trigger_remote_audit(
                    domain=domain,
                    contact_email=email,
                    business_name=business_name,
                    niche=niche,
                    city=city
                )
        except Exception as e:
            print(f"  ❌ Database insert error for {domain}: {str(e)}")

        time.sleep(1)

    return discovered_count

def run_global_discovery():
    """Iterates through target niches and cities with a delay to avoid rate limits."""
    print("🌐 Launching Live B2B Lead Discovery Run...")
    total_new_leads = 0

    for niche in TARGET_NICHES:
        for city in TARGET_CITIES:
            added = discover_leads_for_target(niche=niche, city=city)
            total_new_leads += added
            time.sleep(2)

    print(f"\n✨ Global discovery run complete. Total new leads added & queued: {total_new_leads}")

if __name__ == "__main__":
    run_global_discovery()