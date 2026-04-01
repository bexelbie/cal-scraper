"""HTTP page fetcher for moravska-galerie.cz event listings.

Fetches all paginated event listing pages with dynamic page count discovery,
polite rate limiting (1-second delay), and graceful error handling.

Exports:
    fetch_all_pages — fetch all pages of events, return list of HTML strings
    fetch_page — fetch a single URL, return HTML or None on error
    ScrapingError — raised when scraping cannot produce usable results
"""

import json
import logging
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.moravska-galerie.cz/program/deti-a-rodiny/"
USER_AGENT = "cal-scraper/0.1 (Czech gallery calendar; +https://github.com/bexelbie/cal-scraper)"
REQUEST_DELAY = 1.0  # seconds between page fetches
REQUEST_TIMEOUT = 30  # seconds per request
FAILURE_THRESHOLD = 0.5  # bail if more than 50% of pages fail


class ScrapingError(Exception):
    """Raised when scraping cannot produce usable results."""


def _get_page_url(base_url: str, page: int) -> str:
    """Build the URL for a given page number.

    Page 1 returns base_url unchanged.
    Page N (N>=2) returns base_url + page/{N}/.
    """
    if page == 1:
        return base_url
    if not base_url.endswith("/"):
        base_url = base_url + "/"
    return f"{base_url}page/{page}/"


def _discover_max_pages(html: str) -> int:
    """Parse max_num_pages from the data-settings JSON on div.ecs-posts.

    Returns 1 if the element or attribute is missing or unparseable.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        container = soup.select_one("div.ecs-posts")
        if container and container.get("data-settings"):
            settings = json.loads(container["data-settings"])
            return settings.get("max_num_pages", 1)
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass
    return 1


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


def fetch_all_pages(base_url: str = BASE_URL) -> list[str]:
    """Fetch all paginated event listing pages.

    1. Creates a session with a descriptive User-Agent.
    2. Fetches page 1 and discovers max pages from data-settings JSON.
    3. Fetches pages 2..max_pages with 1-second delay between requests.
    4. Raises ScrapingError if the first page fails or majority of pages fail.

    Returns a list of HTML strings (one per successfully fetched page).
    """
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    # Fetch page 1
    page1_html = fetch_page(_get_page_url(base_url, 1), session)
    if page1_html is None:
        raise ScrapingError("Failed to fetch first page")

    max_pages = _discover_max_pages(page1_html)
    logger.info("Discovered %d pages of events", max_pages)

    pages: list[str] = [page1_html]
    failures = 0

    for page_num in range(2, max_pages + 1):
        time.sleep(REQUEST_DELAY)
        url = _get_page_url(base_url, page_num)
        html = fetch_page(url, session)
        if html is None:
            failures += 1
            logger.warning("Page %d failed, continuing...", page_num)
        else:
            pages.append(html)

    # Bail if majority of subsequent pages failed
    subsequent_pages = max(max_pages - 1, 1)
    if failures / subsequent_pages > FAILURE_THRESHOLD:
        raise ScrapingError(
            f"Too many failures: {failures}/{max_pages - 1} pages failed"
        )

    return pages
