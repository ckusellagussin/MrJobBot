# src/jobs.py
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional
from urllib.parse import quote
from sources.linkedin import fetch_linkedin_jobs
from sources.workday import fetch_workday_jobs

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
EXCLUDE_TERMS = [
    "data collection",
    "data collector",
    "data entry",
]

WORKDAY_SITES = [
    # Add company-specific workday tenants here as you discover them.
    # Example:
    # {"tenant": "kainos", "site": "kainos", "wd_server": "wd3"},
]

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

        candidates = [a, card]
        for node in candidates:
            if not node:
                continue
            h3 = node.find("h3") if hasattr(node, "find") else None
            h4 = node.find("h4") if hasattr(node, "find") else None
            loc = None
            if hasattr(node, "select_one"):
                loc = node.select_one(".job-search-card__location, .topcard__flavor--bullet")
            title = title or (h3.get_text(" ", strip=True) if h3 else "")
            company = company or (h4.get_text(" ", strip=True) if h4 else "")
            location = location or (loc.get_text(" ", strip=True) if loc else "")

        if not title:
            title = a.get_text(" ", strip=True)

        if not title or is_excluded_title(title):
            continue

        url = href.split("?")[0]
        results.append(
            {
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
            }
        )
    return results

def fetch_linkedin_jobs() -> List[Dict]:
    all_jobs = []
    for query in LINKEDIN_QUERIES:
        try:
            url = build_linkedin_url(query)
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            all_jobs.extend(parse_linkedin_search(r.text))
            time.sleep(1.5)
        except Exception as e:
            print(f"[linkedin] {query}: {e}")
    return dedupe_jobs(all_jobs)

def fetch_workday_jobs() -> List[Dict]:
    jobs = []
    for site in WORKDAY_SITES:
        try:
            tenant = site["tenant"]
            name = site["site"]
            wd_server = site.get("wd_server", "wd3")
            url = f"https://{tenant}.{wd_server}.myworkdayjobs.com/wday/cxs/{tenant}/{name}/jobs"
            headers = {
                **HEADERS,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Referer": f"https://{tenant}.{wd_server}.myworkdayjobs.com/en-US/{name}",
            }
            payload = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
            r = requests.post(url, json=payload, headers=headers, timeout=20)
            r.raise_for_status()
            data = r.json()

            for item in data.get("jobPostings", []):
                title = item.get("title", "")
                if not title or is_excluded_title(title):
                    continue
                loc = item.get("locationsText") or item.get("locationText") or ""
                detail = item.get("externalPath") or ""
                job_url = f"https://{tenant}.{wd_server}.myworkdayjobs.com{detail}" if detail else item.get("jobTitle") or ""
                jobs.append(
                    {
                        "id": item.get("bulletFields", {}).get("jobReqId") or job_url or title,
                        "title": title,
                        "company": item.get("company", name),
                        "location": loc,
                        "salary": "",
                        "url": job_url,
                        "apply_url": job_url,
                        "source": "workday",
                        "description": item.get("jobDescription", ""),
                        "skills": "",
                        "legitimacy_check": "Listed on public Workday jobs API",
                    }
                )
        except Exception as e:
            print(f"[workday] {site}: {e}")
    return dedupe_jobs(jobs)

def fetch_jobs() -> List[Dict]:
    jobs = []
    jobs.extend(fetch_linkedin_jobs())
    jobs.extend(fetch_workday_jobs())
    return dedupe_jobs(jobs)