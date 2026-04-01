"""VIDA! Science Center — family events and lab workshops scraper."""

from __future__ import annotations

from cal_scraper.models import Event
from cal_scraper.sites import SiteConfig, register

SITE_CONFIG = SiteConfig(
    name="vida",
    cal_name="VIDA! Science Center – Family Events (unofficial, in CZ)",
    source_url="http://vida.cz/doprovodny-program",
    prodid="-//cal-scraper//vida//CS",
    default_filename="vida.ics",
    cal_desc=(
        "Unofficial scrape — family events and lab workshops, Brno area only"
        " (After Dark 18+ excluded)."
        " Source: http://vida.cz/doprovodny-program"
    ),
)
register(SITE_CONFIG)


def scrape(verbose: bool = False, **kwargs) -> list[Event]:
    """Scrape family events and lab workshops from VIDA! Science Center."""
    from cal_scraper.sites.vida.fetcher import (
        fetch_events_pages,
        fetch_workshops_page,
    )
    from cal_scraper.sites.vida.extractor import (
        extract_events_from_listing,
        extract_workshops,
    )

    pages = fetch_events_pages(verbose=verbose)
    events = extract_events_from_listing(pages)

    workshop_html = fetch_workshops_page(verbose=verbose)
    workshops = extract_workshops(workshop_html)

    combined = events + workshops
    combined.sort(key=lambda e: e.dtstart)
    return combined
