"""HTTP fetcher for VIDA! Science Center event pages."""

from __future__ import annotations

import logging
import time

from bs4 import BeautifulSoup

from cal_scraper.http_client import fetch

logger = logging.getLogger(__name__)

BASE_URL = "http://vida.cz"
EVENTS_URL = f"{BASE_URL}/doprovodny-program"
WORKSHOPS_URL = f"{BASE_URL}/doprovodny-program/labodilny"


def fetch_events_pages(verbose: bool = False) -> list[str]:
    """Fetch all paginated event listing pages.

    Returns a list of HTML strings, one per page.
    """
    if verbose:
        logger.info("Fetching VIDA events page 1: %s", EVENTS_URL)

    resp = fetch(EVENTS_URL, timeout=30)
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
        resp = fetch(url, timeout=30)
        resp.raise_for_status()
        pages.append(resp.text)
        start += 12

    return pages


def fetch_workshops_page(verbose: bool = False) -> str:
    """Fetch the lab workshops page.

    Returns the HTML string.
    """
    if verbose:
        logger.info("Fetching VIDA workshops page: %s", WORKSHOPS_URL)

    resp = fetch(WORKSHOPS_URL, timeout=30)
    resp.raise_for_status()
    return resp.text
