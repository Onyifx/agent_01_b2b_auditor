import time
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def audit_website(url: str) -> dict:
    """
    Audits a target domain for speed, SSL configuration, SEO title, and mobile responsiveness.
    """
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path

    report = {
        "domain": domain,
        "url": url,
        "is_ssl": parsed.scheme == "https",
        "load_time_seconds": 0.0,
        "missing_title": True,
        "missing_viewport": True,
        "status_code": None,
        "top_errors": []
    }

    try:
        start_time = time.time()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, timeout=10, headers=headers)
        elapsed_time = round(time.time() - start_time, 2)

        report["load_time_seconds"] = elapsed_time
        report["status_code"] = response.status_code

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # 1. Check title tag
            title_tag = soup.find("title")
            if title_tag and title_tag.text.strip():
                report["missing_title"] = False

            # 2. Check viewport meta tag
            viewport_tag = soup.find("meta", attrs={"name": lambda v: v and v.lower() == "viewport"})
            if viewport_tag:
                report["missing_viewport"] = False

            # 3. Check performance threshold
            if elapsed_time > 3.0:
                report["top_errors"].append(f"Slow load time: {elapsed_time}s (target is < 2.0s)")

        else:
            report["top_errors"].append(f"Server returned HTTP status code: {response.status_code}")

    except requests.exceptions.SSLError:
        report["is_ssl"] = False
        report["top_errors"].append("SSL certificate error: connection is insecure")
    except requests.exceptions.RequestException as e:
        report["top_errors"].append(f"Failed to reach website: {str(e)}")

    if report["missing_title"]:
        report["top_errors"].append("Missing or empty <title> tag")
    if report["missing_viewport"]:
        report["top_errors"].append("Missing mobile viewport tag (<meta name=\"viewport\">)")

    return report

if __name__ == "__main__":
    test_domain = "example.com"
    print(f"Auditing target: {test_domain}...")
    audit_results = audit_website(test_domain)
    print("\n--- Audit Results ---")
    print(json.dumps(audit_results, indent=2))