import re
import time
import requests
from bs4 import BeautifulSoup

SEARCH_QUERIES = [
    "SOC Analyst",
    "Security Operations Center Analyst",
    "SOC L1",
    "Junior Security Analyst",
]

EXCLUDE_TITLES = ["data collection", "data collector", "data entry"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

def build_url(query: str, start: int = 0) -> str:
    base = "https://www.linkedin.com/jobs/search/"
    params = (
        f"?keywords={requests.utils.quote(query)}"
        f"&f_TPR=r86400"   # posted in last 24 hours
        f"&sortBy=DD"       # newest first
        f"&start={start}"
    )
    return base + params

def parse_jobs(html: str, source_query: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    cards = soup.find_all("div", class_=re.compile(r"job-search-card|base-card"))
    for card in cards:
        try:
            title_tag = card.find("h3")
            company_tag = card.find("h4")
            location_tag = card.find("span", class_=re.compile(r"job-search-card__location"))
            link_tag = card.find("a", href=True)

            title = title_tag.get_text(strip=True) if title_tag else ""
            company = company_tag.get_text(strip=True) if company_tag else ""
            location = location_tag.get_text(strip=True) if location_tag else ""
            url = link_tag["href"].split("?")[0] if link_tag else ""

            if not title or not url:
                continue

            title_lower = title.lower()
            if any(excl in title_lower for excl in EXCLUDE_TITLES):
                continue

            jobs.append({
                "id": url,
                "title": title,
                "company": company,
                "location": location,
                "salary": "",
                "url": url,
                "apply_url": url,
                "source": "linkedin",
                "description": "",
                "skills": "",
                "legitimacy_check": "Listed on LinkedIn",
            })
        except Exception:
            continue
    return jobs

def fetch_jobs() -> list:
    all_jobs = []
    seen_ids = set()

    for query in SEARCH_QUERIES:
        try:
            url = build_url(query)
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            jobs = parse_jobs(resp.text, query)
            for job in jobs:
                if job["id"] not in seen_ids:
                    seen_ids.add(job["id"])
                    all_jobs.append(job)
            time.sleep(2)  # polite delay between queries
        except Exception as e:
            print(f"[linkedin] Failed for query '{query}': {e}")

    return all_jobs