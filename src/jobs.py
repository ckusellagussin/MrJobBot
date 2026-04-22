def fetch_jobs():
    return [
        {
            "id": "example-1",
            "title": "SOC Analyst Level 1",
            "company": "Example Security Ltd",
            "location": "Remote",
            "salary": 45000,
            "url": "https://example.com/jobs/soc-analyst-1",
            "apply_url": "https://example.com/jobs/soc-analyst-1/apply",
            "source": "company",
            "legitimacy_check": "Direct company career page",
        },
        {
            "id": "example-2",
            "title": "Data Collection Analyst",
            "company": "Example Corp",
            "location": "Remote",
            "salary": 50000,
            "url": "https://example.com/jobs/data-collection",
            "apply_url": "https://example.com/jobs/data-collection/apply",
            "source": "jobboard",
            "legitimacy_check": "Excluded by title filter",
        },
    ]
