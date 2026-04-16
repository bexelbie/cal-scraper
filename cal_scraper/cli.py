"""CLI entry point for cal-scraper.

Wires the full pipeline: select sites → scrape → generate ICS → write files.
Registered as the ``cal-scraper`` console command via pyproject.toml.

Public API:
    main(argv) — parse arguments, run pipeline, write .ics files
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from cal_scraper.ics_generator import events_to_ics
from cal_scraper.models import Event
from cal_scraper.sites import SITE_REGISTRY
from cal_scraper.translator import TranslationError, load_azure_config, translate_events

# Trigger site registration on import
import cal_scraper.sites.moravska_galerie  # noqa: F401
import cal_scraper.sites.hvezdarna  # noqa: F401
import cal_scraper.sites.ikea_brno  # noqa: F401
import cal_scraper.sites.vida  # noqa: F401 — triggers registration


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------


def _summarize(events: list[Event], output_path: str) -> None:
    """Print a human-readable summary of the scraping result to stdout."""
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
        description="Scrape event calendars → iCal files",
    )
    parser.add_argument(
        "--site",
        "-s",
        nargs="*",
        choices=list(SITE_REGISTRY.keys()),
        default=None,
        help="Sites to scrape (default: all registered sites)",
    )
    parser.add_argument(
        "--output-dir",
        "-d",
        default=".",
        help="Output directory for .ics files (default: current directory)",
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
        help="Print ICS to stdout instead of writing to files",
    )
    parser.add_argument(
        "--no-details",
        action="store_true",
        help="Skip fetching individual event detail pages (faster, less data)",
    )
    parser.add_argument(
        "--translate",
        action="store_true",
        help=(
            "Translate events to bilingual English/Czech using Azure OpenAI. "
            "Requires AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, "
            "AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION env vars."
        ),
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    selected = args.site if args.site is not None else list(SITE_REGISTRY.keys())
    output_dir = Path(args.output_dir)

    # Load translation config once if --translate is requested
    azure_config: dict[str, str] | None = None
    if args.translate:
        try:
            azure_config = load_azure_config()
        except TranslationError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    errors = 0

    for site_name in selected:
        config = SITE_REGISTRY[site_name]
        site_module = _import_site(site_name)

        try:
            events = site_module.scrape(
                verbose=args.verbose, no_details=args.no_details
            )
        except Exception as exc:
            print(f"Error [{site_name}]: {exc}", file=sys.stderr)
            errors += 1
            continue

        if not events:
            print(
                f"Error [{site_name}]: no events found. The website template may "
                "have changed — check that selectors still match.",
                file=sys.stderr,
            )
            errors += 1
            continue

        if azure_config is not None:
            print(f"Translating {len(events)} events for {site_name}...",
                  file=sys.stderr)
            events = translate_events(events, azure_config)

        ics_content = events_to_ics(
            events,
            cal_name=config.cal_name,
            source_url=config.source_url,
            prodid=config.prodid,
            cal_desc=config.cal_desc,
        )

        if args.dry_run:
            print(ics_content)
            _summarize(events, "(stdout)")
        else:
            out_path = output_dir / config.default_filename
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(ics_content)
            _summarize(events, str(out_path))

    return 1 if errors else 0


def _import_site(name: str):
    """Import and return the site module for a registered site name."""
    import importlib

    # Convert site name (e.g. "moravska-galerie") to module path
    module_name = name.replace("-", "_")
    return importlib.import_module(f"cal_scraper.sites.{module_name}")


if __name__ == "__main__":
    sys.exit(main())
