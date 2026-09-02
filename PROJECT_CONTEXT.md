---
kind: service
purpose: scrape Brno cultural events into iCalendar feeds and an HTML index
visibility: public
---

# cal-scraper - project context

Cal-scraper reads public Czech cultural-venue pages and produces unofficial
`.ics` feeds plus an HTML index. It supports direct CLI runs and a containerized
systemd timer deployment.

## Runtime

- Python 3.10+
- `requests`, Beautiful Soup, `lxml`, and `icalendar`
- Europe/Prague timezone for event data
- Static HTML only; no browser automation
- Optional Azure OpenAI translation configured through `cal-scraper.env`

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

Tests must not depend on live venue sites. Keep scraping polite and preserve
source-language event text unless translation is explicitly enabled.

## Delivery

- `cal-scraper.container` and `cal-scraper.timer` define the systemd Quadlet
  deployment.
- `.github/workflows/check-base-image.yml` checks the mutable container base on
  the first day of each month at 06:00 UTC and supports manual runs.
- Automated reports follow
  `~/repos/agentic-controller/REPORT_CONTRACT.md`.
- Publisher registration and heartbeat policy live in
  `~/repos/infra/systems/agentic-controller-jobs.toml`.

## Secrets

`cal-scraper.env` is ignored and must never be committed. GitHub report
submission uses the repository `NOTIFICATION_URL` secret.

## Pointers

- Deployment host topology: `~/repos/infra/systems/vps-flatcar.md`
- Home Assistant report queue topology:
  `~/repos/infra/systems/home-assistant.md`
