"""Site registry for cal-scraper.

Each site module lives in a sub-package and exposes:
    scrape(verbose: bool = False) -> list[Event]
    SITE_CONFIG: SiteConfig
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class SiteConfig:
    """Per-site configuration for calendar generation."""
    name: str              # short key e.g. "moravska-galerie"
    cal_name: str          # X-WR-CALNAME value
    source_url: str        # base URL of the scraped site section
    prodid: str            # PRODID value for ICS
    default_filename: str  # default output filename
    cal_desc: str = ""     # X-WR-CALDESC override (auto-generated if empty)

# Registry populated by site __init__ modules
SITE_REGISTRY: dict[str, SiteConfig] = {}


def register(config: SiteConfig) -> None:
    """Register a site configuration."""
    SITE_REGISTRY[config.name] = config
