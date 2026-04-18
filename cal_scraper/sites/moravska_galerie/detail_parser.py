"""Detail page parser for enriching events with full description, price, and reservation info."""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from cal_scraper.http_client import fetch
from cal_scraper.sites.moravska_galerie.fetcher import USER_AGENT
from cal_scraper.models import Event

logger = logging.getLogger(__name__)

CONTENT_SELECTOR = (
    '[data-widget_type="theme-post-content.default"] .elementor-widget-container'
)

# Price pattern: "V – 250 Kč (na den)" or "V – 100 / 50 Kč sourozenec"
_RE_PRICE = re.compile(r"V\s*[\u2013\u2014\u2012\u2015–-]\s*(.+?Kč[^\n]*)", re.IGNORECASE)

# Email pattern
_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# Czech phone pattern: 3-digit groups like "724 543 722" or continuous "724543722"
_RE_PHONE = re.compile(r"\b\d{3}\s?\d{3}\s?\d{3}\b")

DETAIL_DELAY = 1.0  # seconds between detail page requests


def _fetch_detail_html(url: str) -> str | None:
    """Fetch a single detail page. Returns HTML or None on failure."""
    try:
        resp = fetch(url, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        logger.warning("Failed to fetch detail page %s: %s", url, exc)
        return None


def _extract_detail(html: str) -> tuple[str, str, str]:
    """Extract (full_description, price, reservation) from a detail page HTML.

    Returns tuple of strings; empty string for fields not found.
    """
    soup = BeautifulSoup(html, "lxml")
    content_el = soup.select_one(CONTENT_SELECTOR)
    if content_el is None:
        return "", "", ""

    # Full description — all text from the content widget
    full_text = content_el.get_text(separator="\n").strip()
    # Clean up: replace non-breaking spaces
    full_text = full_text.replace("\xa0", " ")

    # Extract price
    price = ""
    price_match = _RE_PRICE.search(full_text)
    if price_match:
        price = price_match.group(0).strip()

    # Extract reservation info
    reservation_parts: list[str] = []
    emails = _RE_EMAIL.findall(full_text)
    phones = _RE_PHONE.findall(full_text)
    if emails:
        reservation_parts.extend(emails)
    if phones:
        reservation_parts.extend(phones)
    reservation = ", ".join(reservation_parts)

    # Clean description: remove the price line from description text
    description = full_text
    if price_match:
        description = full_text[: price_match.start()] + full_text[price_match.end() :]
    description = re.sub(r"\n{3,}", "\n\n", description).strip()

    return description, price, reservation


def enrich_events(events: list[Event], delay: float = DETAIL_DELAY) -> list[Event]:
    """Enrich events with data from their detail pages.

    Fetches each event's detail page URL and extracts:
    - Full description (replaces listing excerpt)
    - Price information
    - Reservation contact info

    Skips events with no URL. Politely delays between requests.
    Returns the same list with fields updated in-place.
    """
    urls_seen: set[str] = set()

    for i, event in enumerate(events):
        if not event.url or event.url in urls_seen:
            # For multi-slot events sharing the same URL, copy from first
            for prev in events[:i]:
                if prev.url == event.url:
                    event.description = prev.description
                    event.price = prev.price
                    event.reservation = prev.reservation
                    break
            continue

        urls_seen.add(event.url)

        if len(urls_seen) > 1:
            time.sleep(delay)

        logger.info("Fetching detail: %s", event.url)
        html = _fetch_detail_html(event.url)
        if html is None:
            continue

        description, price, reservation = _extract_detail(html)
        if description:
            event.description = description
        if price:
            event.price = price
        if reservation:
            event.reservation = reservation

    return events
