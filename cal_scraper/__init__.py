"""Cal-scraper: Moravská galerie children/family events → iCal feed."""

from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("cal-scraper")
except Exception:  # package not installed (editable / dev checkout)
    __version__ = "0.0.0-dev"
