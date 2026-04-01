"""HTML event extractor for Moravská galerie Elementor event cards.

Parses Elementor-based event listing pages into Event objects using
CSS selectors derived from the site's widget data-id attributes.

Integrates with cal_scraper.date_parser for Czech date string parsing.
"""

import logging

from bs4 import BeautifulSoup, Tag

from cal_scraper.sites.moravska_galerie.date_parser import parse_dates
from cal_scraper.models import Event

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Selector constants (from ARCHITECTURE.md verified selectors)
# ---------------------------------------------------------------------------

ARTICLE_SELECTOR = "article.elementor-post"
TITLE_SELECTOR = '[data-id="ff31590"] a'
DATE_SELECTOR = '[data-id="fe5263e"] .elementor-widget-container'
VENUE_SELECTOR = '[data-id="d2f8856"] .elementor-widget-container'
DESCRIPTION_SELECTOR = '[data-id="16d0837"] .elementor-widget-container'


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------


def _clean_text(text: str) -> str:
    """Normalize whitespace: replace non-breaking spaces with regular spaces, strip."""
    # Replace \xa0 (non-breaking space, U+00A0) with regular space
    text = text.replace("\xa0", " ")
    return text.strip()


# ---------------------------------------------------------------------------
# Single event extraction
# ---------------------------------------------------------------------------


def _extract_events_from_article(article: Tag) -> list[Event]:
    """Extract Events from an Elementor article tag.

    Returns one Event per time slot. Multi-slot dates (e.g. "15 H / 16 H / 17 H")
    produce multiple Events sharing the same title, venue, and description.
    Returns an empty list if critical fields are missing.
    """
    # Title (critical — skip if missing)
    title_el = article.select_one(TITLE_SELECTOR)
    if title_el is None:
        classes = article.get("class", [])
        logger.warning("Skipping event: no title element found in article %s", classes)
        return []

    title = _clean_text(title_el.get_text())
    url = title_el.get("href", "")

    # ENHN-01: detect sold-out events
    sold_out = "VYPRODÁNO" in title.upper()

    # Date (critical — skip if missing)
    date_el = article.select_one(DATE_SELECTOR)
    if date_el is None:
        logger.warning("Skipping event: no date element found for '%s'", title)
        return []

    date_text = _clean_text(date_el.get_text())
    parsed_dates = parse_dates(date_text)
    if not parsed_dates:
        logger.warning("Skipping event: unrecognized date format for '%s': %r", title, date_text)
        return []

    # Venue (non-critical — empty string fallback)
    venue_el = article.select_one(VENUE_SELECTOR)
    venue = _clean_text(venue_el.get_text()) if venue_el else ""

    # Description (non-critical — empty string fallback)
    desc_el = article.select_one(DESCRIPTION_SELECTOR)
    description = _clean_text(desc_el.get_text()) if desc_el else ""

    return [
        Event(
            title=title,
            dtstart=parsed.dtstart,
            dtend=parsed.dtend,
            all_day=parsed.all_day,
            venue=venue,
            description=description,
            url=url,
            raw_date=parsed.raw_text,
            sold_out=sold_out,
        )
        for parsed in parsed_dates
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_events_from_html(html: str) -> list[Event]:
    """Extract all valid Event objects from an HTML page of Elementor event cards.

    Skips articles missing critical fields (title, date) with warning logs.
    Warns if no article elements are found — likely a template/selector change.
    """
    soup = BeautifulSoup(html, "lxml")
    articles = soup.select(ARTICLE_SELECTOR)

    if not articles:
        logger.warning(
            "No article elements matched selector %r — "
            "the site template may have changed",
            ARTICLE_SELECTOR,
        )

    events: list[Event] = []

    for article in articles:
        events.extend(_extract_events_from_article(article))

    return events


def extract_all_events(pages: list[str]) -> list[Event]:
    """Extract events from multiple HTML pages and return combined list."""
    all_events: list[Event] = []
    for page_html in pages:
        all_events.extend(extract_events_from_html(page_html))
    return all_events
