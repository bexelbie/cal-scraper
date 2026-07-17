"""VIDA! Science Center — family events scraper."""

from __future__ import annotations

from datetime import date, datetime

from cal_scraper.models import Event
from cal_scraper.sites import SiteConfig, register

SITE_CONFIG = SiteConfig(
    name="vida",
    cal_name="VIDA! Science Center – Family Events (unofficial, in CZ)",
    source_url="http://vida.cz/doprovodny-program",
    prodid="-//cal-scraper//vida//CS",
    default_filename="vida.ics",
    cal_desc=(
        "Unofficial scrape — daily in-house program from VIDA's per-day calendar"
        " plus Brno-area/off-site special family events"
        " (After Dark 18+ excluded)."
        " Source: http://vida.cz/doprovodny-program"
    ),
)
register(SITE_CONFIG)


def _slug_date_key(event: Event) -> tuple[str, date]:
    """Build the (slug, date) dedup key used for merging VIDA sources."""
    slug = event.url.rstrip("/").split("/")[-1]
    dt = event.dtstart.date() if isinstance(event.dtstart, datetime) else event.dtstart
    return slug, dt


def scrape(verbose: bool = False, **kwargs) -> list[Event]:
    """Scrape and merge VIDA listing events with per-day program events."""
    from cal_scraper.sites.vida.fetcher import (
        fetch_calendar_days,
        fetch_events_pages,
    )
    from cal_scraper.sites.vida.extractor import (
        extract_events_from_listing,
        extract_program_from_calendar,
    )

    pages = fetch_events_pages(verbose=verbose)
    listing = extract_events_from_listing(pages)
    program_days = fetch_calendar_days(verbose=verbose)
    program = extract_program_from_calendar(program_days)

    program_keys = {_slug_date_key(ev) for ev in program}
    filtered_listing = [ev for ev in listing if _slug_date_key(ev) not in program_keys]

    combined = program + filtered_listing
    combined.sort(key=lambda e: e.dtstart)
    return combined
