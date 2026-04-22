import json
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

from jobs import fetch_jobs

load_dotenv()

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
TARGET_ROLE = os.getenv("TARGET_ROLE", "SOC Analyst Level 1").lower()
MIN_SALARY = int(os.getenv("MIN_SALARY", "0"))
LONDON_AVG_SALARY = int(os.getenv("LONDON_AVG_SALARY", "0"))
STATE_FILE = Path("state.json")


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding='utf-8'))
    return {"seen": []}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding='utf-8')


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


def is_valid_role(job):
    title = normalize(job.get("title"))
    company = normalize(job.get("company"))
    location = normalize(job.get("location"))
    source = normalize(job.get("source"))
    salary = salary_value(job)

    if TARGET_ROLE not in title:
        return False
    if "data collection" in title:
        return False
    if salary and salary < MIN_SALARY:
        return False
    if company == "" or location == "":
        return False
    if source not in {"linkedin", "workday", "company", "jobboard"}:
        return False
    return True


def format_message(job):
    salary = job.get("salary", "unknown")
    apply_url = job.get("apply_url") or job.get("url")
    extras = []
    if job.get("legitimacy_check"):
        extras.append(f"Legitimacy: {job['legitimacy_check']}")
    if LONDON_AVG_SALARY:
        extras.append(f"London avg benchmark: {LONDON_AVG_SALARY}")
    extra_line = "
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

    jobs = fetch_jobs()
    matches = []

    for job in jobs:
        job_id = str(job.get("id") or job.get("url"))
        if job_id in seen:
            continue
        if not is_valid_role(job):
            continue
        matches.append(job)
        seen.add(job_id)

    if not matches:
        send_discord_message("Prototype 3: no new matching jobs found.")
    else:
        for job in matches:
            send_discord_message(format_message(job))

    state["seen"] = sorted(seen)
    save_state(state)


if __name__ == "__main__":
    main()
