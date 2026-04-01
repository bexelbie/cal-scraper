"""CLI entry point for cal-scraper.

Wires the full pipeline: fetch → extract → generate ICS → write file.
Registered as the ``cal-scraper`` console command via pyproject.toml.

Public API:
    main(argv) — parse arguments, run pipeline, write .ics file
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime

from cal_scraper.detail_parser import enrich_events
from cal_scraper.extractor import extract_all_events
from cal_scraper.fetcher import ScrapingError, fetch_all_pages
from cal_scraper.ics_generator import events_to_ics
from cal_scraper.models import Event

DEFAULT_OUTPUT = "moravska-galerie-deti.ics"


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------


def _summarize(events: list[Event], output_path: str) -> None:
    """Print a human-readable summary of the scraping result to stdout."""
    if not events:
        print("No events found.")
        print(f"Written to {output_path}")
        return

    dates: list[date] = []
    for ev in events:
        d = ev.dtstart
        if isinstance(d, datetime):
            d = d.date()
        dates.append(d)

    min_date = min(dates)
    max_date = max(dates)
    print(f"Scraped {len(events)} events ({min_date} to {max_date})")
    print(f"Written to {output_path}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the cal-scraper pipeline.

    Parameters
    ----------
    argv : list[str] | None
        Command-line arguments.  ``None`` reads from ``sys.argv``.

    Returns
    -------
    int
        0 on success, 1 on error.
    """
    parser = argparse.ArgumentParser(
        prog="cal-scraper",
        description="Scrape Moravská galerie children/family events → iCal file",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=DEFAULT_OUTPUT,
        help=f"Output .ics file path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print ICS to stdout instead of writing to a file",
    )
    parser.add_argument(
        "--no-details",
        action="store_true",
        help="Skip fetching individual event detail pages (faster, less data)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    try:
        pages = fetch_all_pages()
        events = extract_all_events(pages)
        if not args.no_details:
            events = enrich_events(events)
    except ScrapingError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    ics_content = events_to_ics(events)

    if args.dry_run:
        print(ics_content)
    else:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(ics_content)

    _summarize(events, "(stdout)" if args.dry_run else args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
