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

LINKEDIN_QUERIES = [
    "SOC Analyst",
    "Security Operations Center Analyst",
    "SOC L1",
    "Junior Security Analyst",
]
EXCLUDE_TERMS = ["data collection", "data collector", "data entry"]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


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
            company = company or (h4.get_text(" ", strip=True) if h4 else "")# placeholder
