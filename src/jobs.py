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
            h3 = node