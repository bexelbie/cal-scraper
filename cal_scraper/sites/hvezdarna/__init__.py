"""Hvězdárna a planetárium Brno — public planetarium shows scraper."""

from __future__ import annotations
from cal_scraper.models import Event
from cal_scraper.sites import SiteConfig, register

SITE_CONFIG = SiteConfig(
    name="hvezdarna",
    cal_name="Hvězdárna Brno – Public Shows (unofficial, in CZ)",
    source_url="https://www.hvezdarna.cz/",
    prodid="-//cal-scraper//hvezdarna//CS",
    default_filename="hvezdarna.ics",
    cal_desc="Unofficial scrape — public shows only (school programs excluded). Source: https://www.hvezdarna.cz/",
)
register(SITE_CONFIG)


def scrape(verbose: bool = False, **kwargs) -> list[Event]:
    """Scrape public planetarium shows from Hvězdárna Brno."""
    from cal_scraper.sites.hvezdarna.fetcher import fetch_all_weeks
    from cal_scraper.sites.hvezdarna.extractor import extract_events

    pages = fetch_all_weeks(verbose=verbose)
    events = extract_events(pages)
    return events
