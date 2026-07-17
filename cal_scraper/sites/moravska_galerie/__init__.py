"""Moravská galerie — children/family events scraper."""

from __future__ import annotations

from bs4 import BeautifulSoup

from cal_scraper.models import Event
from cal_scraper.sites import SiteConfig, register

SITE_CONFIG = SiteConfig(
    name="moravska-galerie",
    cal_name="Moravská galerie – Children & Families (unofficial, in CZ)",
    source_url="https://moravska-galerie.cz/program/deti-a-rodiny/",
    prodid="-//cal-scraper//moravska-galerie//CS",
    default_filename="moravska-galerie.ics",
    cal_desc="Unofficial scrape — children & family events only. Source: https://moravska-galerie.cz/program/deti-a-rodiny/",
)
register(SITE_CONFIG)


def scrape(verbose: bool = False, no_details: bool = False) -> list[Event]:
    """Scrape all children/family events from Moravská galerie."""
    from cal_scraper.sites.moravska_galerie.fetcher import fetch_all_pages
    from cal_scraper.sites.moravska_galerie.extractor import extract_all_events
    from cal_scraper.sites.moravska_galerie.detail_parser import enrich_events

    pages = fetch_all_pages()
    if not any(BeautifulSoup(page, "lxml").select("article.elementor-post") for page in pages):
        raise RuntimeError(
            "Moravska galerie listing structure changed: missing 'article.elementor-post' cards"
        )
    events = extract_all_events(pages)
    if not no_details:
        events = enrich_events(events)
    return events
