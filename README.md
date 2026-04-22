# Prototype 3

Discord job-alert bot for SOC Analyst Level 1 roles.

## Setup

1. Add your Discord webhook to GitHub Secrets as `DISCORD_WEBHOOK_URL`.
2. Add optional repo variables:
   - `TARGET_ROLE`
   - `MIN_SALARY`
   - `LONDON_AVG_SALARY`
3. Push this repo.
4. GitHub Actions will run every 15 minutes.

## Local test

```bash
python -m pip install -r requirements.txt
python src/main.py
```
