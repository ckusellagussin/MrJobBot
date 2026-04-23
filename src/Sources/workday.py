import re
from typing import Dict, List

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

WORKDAY_SITES = [
    # Add tenant + site pairs here, example:
    # {"tenant": "company", "site": "Careers"}
]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


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
                loc = item.get("locationsText") or item.get("locationText") or ""
                detail = item.get("externalPath") or ""
                job_url = f"https://{tenant}.{wd_server}.myworkdayjobs.com{detail}" if detail else ""
                jobs.append({
                    "id": item.get("bulletFields", {}).get("jobReqId") or job_url or title,
                    "title": title,
                    "company": item.get("company", name),
                    "location": loc,
                    "salary": "",
                    "url": job_url,
                    "apply_url": job_url,
                    "source": "workday",

