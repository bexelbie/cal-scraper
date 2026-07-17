"""HTTP fetcher for VIDA! Science Center event pages."""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from cal_scraper.http_client import fetch

logger = logging.getLogger(__name__)

BASE_URL = "http://vida.cz"
EVENTS_URL = f"{BASE_URL}/doprovodny-program"
CALENDAR_URL = "https://vida.cz/index.php/kalendar"
PRAGUE_TZ = ZoneInfo("Europe/Prague")
MAX_CALENDAR_DAYS = 120
EMPTY_STREAK_STOP = 14


def fetch_events_pages(verbose: bool = False) -> list[str]:
    """Fetch all paginated event listing pages.

    Returns a list of HTML strings, one per page.
    """
    if verbose:
        logger.info("Fetching VIDA events page 1: %s", EVENTS_URL)

    resp = fetch(EVENTS_URL, timeout=30, verify=False)
    resp.raise_for_status()
    pages = [resp.text]

    # Discover max page from pagination links like ?start=12, ?start=24 …
    soup = BeautifulSoup(resp.text, "lxml")
    max_start = 0
    for link in soup.select('a[href*="start="]'):
        href = link.get("href", "")
        for part in href.split("?")[-1].split("&"):
            if part.startswith("start="):
                try:
                    val = int(part.split("=")[1])
                    if val > max_start:
                        max_start = val
                except ValueError:
                    pass

    start = 12
    while start <= max_start:
        time.sleep(1)
        url = f"{EVENTS_URL}?start={start}"
        if verbose:
            logger.info("Fetching VIDA events page: %s", url)
        resp = fetch(url, timeout=30, verify=False)
        resp.raise_for_status()
        pages.append(resp.text)
        start += 12

    return pages


def fetch_calendar_days(verbose: bool = False) -> list[tuple[date, str]]:
    """Fetch VIDA per-day program fragments until sustained emptiness or hard cap."""
    day = datetime.now(tz=PRAGUE_TZ).date()
    fetched: list[tuple[date, str]] = []
    empty_streak = 0

    for index in range(MAX_CALENDAR_DAYS):
        if index > 0:
            time.sleep(1)

        if verbose:
            logger.info("Fetching VIDA daily calendar: %s day=%s", CALENDAR_URL, day)

        # ponytail: build the query inline; fetch() has no params kwarg and day.isoformat()/tmpl are URL-safe.
        url = f"{CALENDAR_URL}?tmpl=raw&day={day.isoformat()}"
        resp = fetch(url, timeout=30, verify=False)
        resp.raise_for_status()
        html = resp.text
        fetched.append((day, html))

        has_items = bool(BeautifulSoup(html, "lxml").select("a.cal-item"))
        if has_items:
            empty_streak = 0
        else:
            empty_streak += 1
            if empty_streak >= EMPTY_STREAK_STOP:
                break

        day = day + timedelta(days=1)

    return fetched
