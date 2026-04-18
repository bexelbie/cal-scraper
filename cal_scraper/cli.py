"""CLI entry point for cal-scraper.

Wires the full pipeline: select sites → scrape → generate ICS → write files.
Registered as the ``cal-scraper`` console command via pyproject.toml.

Public API:
    main(argv) — parse arguments, run pipeline, write .ics files
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

from cal_scraper.ics_generator import events_to_ics
from cal_scraper.index_generator import generate_index
from cal_scraper.models import Event
from cal_scraper.sites import SITE_REGISTRY
from cal_scraper.translator import TranslationError, load_azure_config, translate_events

from dataclasses import replace as _replace

# Trigger site registration on import
import cal_scraper.sites.moravska_galerie  # noqa: F401
import cal_scraper.sites.hvezdarna  # noqa: F401
import cal_scraper.sites.ikea_brno  # noqa: F401
import cal_scraper.sites.vida  # noqa: F401 — triggers registration


# ---------------------------------------------------------------------------
# Event description disclaimers
# ---------------------------------------------------------------------------

_DISCLAIMER_CZ = (
    "⚠️ Neoficiální zdroj – ověřte si detaily na webu pořadatele."
)


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


def _write_ics(
    events: list[Event],
    config,
    output_dir: Path,
    args: argparse.Namespace,
    *,
    suffix: str = "",
    translated: bool = False,
) -> None:
    """Generate ICS content and write it to disk (or stdout for --dry-run)."""
    cal_name = config.cal_name
    cal_desc = config.cal_desc
    if translated:
        cal_name = cal_name.replace("in CZ", "EN, auto-translated from CZ")
        cal_desc = f"Auto-translated to English via Azure OpenAI. {cal_desc}"
    else:
        footer = f"\n\n{_DISCLAIMER_CZ}"
        events = [_replace(ev, description=ev.description + footer) for ev in events]

    ics_content = events_to_ics(
        events,
        cal_name=cal_name,
        source_url=config.source_url,
        prodid=config.prodid,
        cal_desc=cal_desc,
    )

    if args.dry_run:
        print(ics_content)
        _summarize(events, "(stdout)")
    else:
        base_name = config.default_filename
        if suffix:
            stem, ext = base_name.rsplit(".", 1)
            base_name = f"{stem}{suffix}.{ext}"
        out_path = output_dir / base_name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: tempfile + rename so readers never see a half-written file
        fd, tmp = tempfile.mkstemp(dir=out_path.parent, suffix=".ics.tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(ics_content)
            os.replace(tmp, out_path)
        except BaseException:
            os.unlink(tmp)
            raise
        _summarize(events, str(out_path))


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
    translate_group = parser.add_mutually_exclusive_group()
    translate_group.add_argument(
        "--no-translate",
        action="store_true",
        help="Skip translation even when Azure OpenAI env vars are present.",
    )
    translate_group.add_argument(
        "--translate-only",
        "--translate",
        action="store_true",
        help=(
            "Only produce translated output (no Czech files). "
            "Requires AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, "
            "AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION env vars."
        ),
    )
    parser.add_argument(
        "--translate-suffix",
        default="-en",
        help=(
            "Suffix for translated output filenames "
            "(default: '-en' → moravska-galerie-en.ics)"
        ),
    )
    parser.add_argument(
        "--filename-suffix",
        default="",
        help=(
            "Suffix to append to output filenames before .ics extension "
            "(e.g., '--filename-suffix=-en' → moravska-galerie-en.ics). "
            "For translated files, use --translate-suffix instead."
        ),
    )
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="Skip generating index.html (generated by default)",
    )
    parser.add_argument(
        "--index-template",
        default=None,
        help="Path to a custom HTML template for the index page",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    selected = args.site if args.site is not None else list(SITE_REGISTRY.keys())
    output_dir = Path(args.output_dir)

    # Resolve translation mode:
    #   --translate-only  → translate required, Czech output suppressed
    #   --no-translate    → translation suppressed
    #   (default)         → auto-detect: translate if Azure vars are present
    azure_config: dict[str, str] | None = None
    translate_only = args.translate_only

    if translate_only:
        # Explicit --translate-only: Azure config is mandatory
        try:
            azure_config = load_azure_config()
        except TranslationError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
    elif not args.no_translate:
        # Default: auto-detect Azure config (translate if available)
        try:
            azure_config = load_azure_config()
        except TranslationError:
            azure_config = None  # silently skip translation

    errors = 0
    succeeded: list[str] = []
    failed: list[str] = []

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
            failed.append(site_name)
            continue

        if not events:
            print(
                f"Error [{site_name}]: no events found. The website template may "
                "have changed — check that selectors still match.",
                file=sys.stderr,
            )
            errors += 1
            failed.append(site_name)
            continue

        # --- Czech output (unless --translate-only) ---
        if not translate_only:
            _write_ics(events, config, output_dir, args, suffix=args.filename_suffix)

        # --- Translated output (when Azure config is available) ---
        if azure_config is not None:
            print(f"Translating {len(events)} events for {site_name}...",
                  file=sys.stderr)
            translated, translation_ok = translate_events(events, azure_config)
            if not translation_ok:
                print(
                    f"Error [{site_name}]: translation failed — "
                    "keeping previous translated file (if any)",
                    file=sys.stderr,
                )
                errors += 1
                if translate_only:
                    failed.append(site_name)
                    continue
            else:
                suffix = args.translate_suffix if not translate_only else args.filename_suffix
                _write_ics(
                    translated, config, output_dir, args,
                    suffix=suffix, translated=True,
                )

        succeeded.append(site_name)

    # Generate index.html unless suppressed or dry-run
    if succeeded and not args.dry_run and not args.no_index:
        tpl_path = Path(args.index_template) if args.index_template else None
        cal_base_url = os.environ.get("CAL_BASE_URL", "").strip()
        index_html = generate_index(
            output_dir, template_path=tpl_path, base_url=cal_base_url,
        )
        index_path = output_dir / "index.html"
        fd, tmp = tempfile.mkstemp(dir=index_path.parent, suffix=".html.tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(index_html)
            os.replace(tmp, index_path)
        except BaseException:
            os.unlink(tmp)
            raise
        print(f"Index written to {index_path}")

    # Final summary for journal/log visibility
    total = len(selected)
    ok = len(succeeded)
    if failed:
        print(
            f"cal-scraper: {ok}/{total} sites OK (failed: {', '.join(failed)})",
            file=sys.stderr,
        )
    else:
        print(f"cal-scraper: {ok}/{total} sites OK", file=sys.stderr)

    return 1 if errors else 0


def _import_site(name: str):
    """Import and return the site module for a registered site name."""
    import importlib

    # Convert site name (e.g. "moravska-galerie") to module path
    module_name = name.replace("-", "_")
    return importlib.import_module(f"cal_scraper.sites.{module_name}")


if __name__ == "__main__":
    sys.exit(main())
