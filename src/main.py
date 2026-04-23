import json
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

from jobs import fetch_jobs

load_dotenv()

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
TARGET_ROLES = [x.strip().lower() for x in os.getenv("TARGET_ROLES", "SOC Analyst Level 1").split(",") if x.strip()]
MIN_SALARY = int(os.getenv("MIN_SALARY", "0"))
LONDON_AVG_SALARY = int(os.getenv("LONDON_AVG_SALARY", "0"))
CV_KEYWORDS = [x.strip().lower() for x in os.getenv("CV_KEYWORDS", "").split(",") if x.strip()]
CV_TEXT = os.getenv("CV_TEXT", "")

STATE_FILE = Path("state.json")

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"seen": []}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

def send_discord_message(content):
    if not WEBHOOK_URL:
        raise RuntimeError("DISCORD_WEBHOOK_URL is missing")
    r = requests.post(WEBHOOK_URL, json={"content": content}, timeout=30)
    r.raise_for_status()

def normalize(text):
    return re.sub(r"\s+", " ", (text or "")).strip().lower()

def salary_value(job):
    salary = job.get("salary")
    if isinstance(salary, int):
        return salary
    if isinstance(salary, str):
        nums = re.findall(r"\d[\d,]*", salary.replace(",", ""))
        if nums:
            return int(nums[0].replace(",", ""))
    return 0

def cv_match(job):
    if not CV_KEYWORDS and not CV_TEXT:
        return True
    haystack = " ".join([
        normalize(job.get("title")),
        normalize(job.get("description", "")),
        normalize(job.get("skills", "")),
        normalize(job.get("company")),
    ])
    if CV_KEYWORDS:
        return any(k in haystack for k in CV_KEYWORDS)
    return any(token in haystack for token in normalize(CV_TEXT).split() if len(token) > 2)

def is_valid_role(job):
    title = normalize(job.get("title", ""))
    company = normalize(job.get("company", ""))
    location = normalize(job.get("location", ""))
    source = normalize(job.get("source", ""))
    salary = salary_value(job)

    if not any(role in title for role in TARGET_ROLES):
        return False
    if "data collection" in title:
        return False
    if salary and salary < MIN_SALARY:
        return False
    if company == "" or location == "":
        return False
    if source not in {"linkedin", "workday", "company", "jobboard"}:
        return False
    if not cv_match(job):
        return False
    return True

def format_message(job):
    salary = job.get("salary", "Not listed")
    apply_url = job.get("apply_url") or job.get("url")
    extras = []
    if job.get("legitimacy_check"):
        extras.append(f"Legitimacy: {job['legitimacy_check']}")
    if LONDON_AVG_SALARY:
        extras.append(f"London avg benchmark: £{LONDON_AVG_SALARY:,}")
    extra_line = "\n" + "\n".join(extras) if extras else ""
" + "
".join(extras) if extras else ""
    return (
        f"**{job['title']}**
"
        f"{job['company']} — {job['location']}
"
        f"Salary: {salary}
"
        f"Source: {job.get('source', 'unknown')}
"
        f"{job.get('url')}
"
        f"Apply: {apply_url}"
        f"{extra_line}"
    )

def main():
    state = load_state()
    seen = set(state.get("seen", []))

    try:
        all_jobs = fetch_jobs()
    except Exception as e:
        send_discord_message(f"MrJobBot error: {e}")
        return

    matches = []
    for job in all_jobs:
        job_id = str(job.get("id") or job.get("url"))
        if job_id in seen:
            continue
        if not is_valid_role(job):
            continue
        matches.append(job)
        seen.add(job_id)

    if not matches:
        send_discord_message(f"MrJobBot: no new matching jobs found for {os.getenv('TARGET_ROLES', 'SOC Analyst Level 1')}.")
    else:
        for job in matches:
            send_discord_message(format_message(job))

    state["seen"] = sorted(seen)
    save_state(state)

if __name__ == "__main__":
    main()
