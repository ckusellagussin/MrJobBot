import os
import re
import time
from typing import Dict, List
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

TARGET_ROLES = [x.strip().lower() for x in os.getenv("TARGET_ROLES", "SOC Analyst Level 1").split(",") if x.strip()]
LINKEDIN_QUERIES = [
    "SOC Analyst",
    "Security Operations Center Analyst",
    "SOC L1",
    "Junior Security Analyst",
]
EXCLUDE_TERMS = ["data collection", "data collector", "data entry"]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def dedupe_jobs(jobs: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for job in jobs:
        key = str(job.get("id") or job.get("url") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(job)
    return out


def is_excluded_title(title: str) -> bool:
    t = normalize(title)
    return any(term in t for term in EXCLUDE_TERMS)


def build_linkedin_url(query: str, start: int = 0) -> str:
    return (
        "https://www.linkedin.com/jobs/search/"
        f"?keywords={quote(query)}"
        "&f_TPR=r86400"
        "&sortBy=DD"
        f"&start={start}"
    )


def parse_linkedin_search(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    cards = soup.select("a.base-card__full-link, a[data-tracking-control-name='public_jobs_jserp-result_search-card']")
    if not cards:
        cards = soup.find_all("a", href=True)

    for a in cards:
        href = a.get("href", "")
        if "/jobs/view/" not in href and "/jobs/search/" not in href:
            continue
        card = a.parent
        title = ""
        company = ""
        location = ""

        for node in [a, card]:
            if not node:
                continue
            h3 = node.find("h3") if hasattr(node, "find") else None
            h4 = node.find("h4") if hasattr(node, "find") else None
            loc = node.select_one(".job-search-card__location, .topcard__flavor--bullet") if hasattr(node, "select_one") else None
            title = title or (h3.get_text(" ", strip=True) if h3 else "")
            company = company or (h4.get_text(" ", strip=True) if h4 else "")
            location = location or (loc.get_text(" ", strip=True) if loc else "")

        if not title:
            title = a.get_text(" ", strip=True)

        if not title or is_excluded_title(title):
            continue

        url = href.split("?")[0]
        results.append({
            "id": url,
            "title": title,
            "company": company or "LinkedIn company",
            "location": location or "",
            "salary": "",
            "url": url,
            "apply_url": url,
            "source": "linkedin",
            "description": "",
            "skills": "",
            "legitimacy_check": "Listed on LinkedIn public jobs search",
        })
    return results


def fetch_linkedin_jobs() -> List[Dict]:
    all_jobs = []
    for query in LINKEDIN_QUERIES:
        try:
            resp = requests.get(build_linkedin_url(query), headers=HEADERS, timeout=20)
            resp.raise_for_status()
            all_jobs.extend(parse_linkedin_search(resp.text))
            time.sleep(1.5)
        except Exception as e:
            print(f"[linkedin] {query}: {e}")
    return dedupe_jobs(all_jobs)


def fetch_workday_jobs() -> List[Dict]:
    return []


def fetch_jobs() -> List[Dict]:
    return dedupe_jobs(fetch_linkedin_jobs() + fetch_workday_jobs())
