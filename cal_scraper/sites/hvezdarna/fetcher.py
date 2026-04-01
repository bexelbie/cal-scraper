"""Week-based page fetcher for Hvězdárna Brno planetarium program.

Discovers the date range from the kalendarInit() JS call, then iterates
week by week from the current Monday until the max date, fetching each
weekly view page.

Exports:
    fetch_all_weeks — fetch all weekly pages, return list of (html, week_start) tuples
    ScrapingError — raised when scraping cannot produce usable results
"""

from __future__ import annotations

import logging
import re
import time
from datetime import date, datetime, timedelta

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://www.hvezdarna.cz/"
USER_AGENT = "cal-scraper/0.1 (Czech planetarium calendar; +https://github.com/bexelbie/cal-scraper)"
REQUEST_DELAY = 1.0  # seconds between page fetches
REQUEST_TIMEOUT = 30  # seconds per request


class ScrapingError(Exception):
    """Raised when scraping cannot produce usable results."""


def _week_url(base_url: str, d: date) -> str:
    """Build the weekly view URL for a given date.

    Uses single-digit month/day (no zero-padding) as the site expects.
    """
    datum = f"{d.year}-{d.month}-{d.day}"
    # Prefer query parameter on the base URL
    return f"{base_url}?type=tyden&datum={datum}"


def _monday_of(d: date) -> date:
    """Return the Monday of the ISO week containing *d*."""
    return d - timedelta(days=d.weekday())


def _parse_max_timestamp(html: str) -> int | None:
    """Extract the max-date Unix timestamp from kalendarInit(current, min, max, ...).

    Returns None if the pattern is not found.
    """
    match = re.search(r"kalendarInit\(\s*\d+\s*,\s*\d+\s*,\s*(\d+)", html)
    if match:
        return int(match.group(1))
    return None


def fetch_page(url: str, session: requests.Session) -> str | None:
    """Fetch a single page and return its HTML body.

    Returns None and logs a warning on any network or HTTP error.
    """
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return None


def fetch_all_weeks(
    base_url: str = BASE_URL, verbose: bool = False
) -> list[tuple[str, date]]:
    """Fetch all weekly programme pages from Hvězdárna Brno.

    1. Fetches the first page (today's week) and discovers the max date
       from the ``kalendarInit(...)`` JS call.
    2. Iterates week by week from the current Monday until past the max date.
    3. Sleeps 1 s between requests.

    Returns a list of ``(html, week_start_monday)`` tuples.
    """
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    today = date.today()
    start_monday = _monday_of(today)

    # Fetch the first page to discover the date range
    first_url = _week_url(base_url, start_monday)
    first_html = fetch_page(first_url, session)
    if first_html is None:
        raise ScrapingError("Failed to fetch first weekly page")

    max_ts = _parse_max_timestamp(first_html)
    if max_ts is None:
        logger.warning("Could not find kalendarInit max date; fetching only current week")
        return [(first_html, start_monday)]

    max_date = datetime.fromtimestamp(max_ts).date()
    if verbose:
        logger.info(
            "Discovered schedule range: %s to %s", start_monday, max_date
        )

    pages: list[tuple[str, date]] = [(first_html, start_monday)]
    current_monday = start_monday + timedelta(days=7)

    while current_monday <= max_date:
        time.sleep(REQUEST_DELAY)
        url = _week_url(base_url, current_monday)
        html = fetch_page(url, session)
        if html is not None:
            pages.append((html, current_monday))
        else:
            logger.warning("Failed to fetch week starting %s, skipping", current_monday)
        current_monday += timedelta(days=7)

    return pages
