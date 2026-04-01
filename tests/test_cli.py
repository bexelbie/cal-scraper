"""Tests for CLI entry point and pipeline wiring."""

import io
import sys
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from cal_scraper.models import PRAGUE_TZ, Event


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

MOCK_EVENTS = [
    Event(
        title="Event 1",
        dtstart=datetime(2026, 4, 8, 16, 0, tzinfo=PRAGUE_TZ),
        dtend=datetime(2026, 4, 8, 18, 0, tzinfo=PRAGUE_TZ),
        all_day=False,
        venue="Venue A",
        description="Desc 1",
        url="https://example.com/1/",
        raw_date="8/4/2026, 16 H",
    ),
    Event(
        title="Event 2",
        dtstart=date(2026, 7, 7),
        dtend=date(2026, 7, 12),
        all_day=True,
        venue="Venue B",
        description="Desc 2",
        url="https://example.com/2/",
        raw_date="7/7 – 11/7/2026",
    ),
]

MOCK_ICS = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n"


def _patch_pipeline(events=None, ics=None, pages=None):
    """Return a dict of patch context managers for the three pipeline functions."""
    if events is None:
        events = MOCK_EVENTS
    if ics is None:
        ics = MOCK_ICS
    if pages is None:
        pages = ["<html>page1</html>"]
    return {
        "fetch": patch("cal_scraper.cli.fetch_all_pages", return_value=pages),
        "extract": patch("cal_scraper.cli.extract_all_events", return_value=events),
        "ics": patch("cal_scraper.cli.events_to_ics", return_value=ics),
    }


# ---------------------------------------------------------------------------
# CLI-01: Argument parsing — --output, -o, --verbose, defaults
# ---------------------------------------------------------------------------


class TestCliArgParsing:
    """CLI argument parsing for --output/-o and --verbose flags."""

    def test_default_output_path(self, tmp_path):
        """main([]) uses default output path moravska-galerie-deti.ics."""
        patches = _patch_pipeline()
        with patches["fetch"], patches["extract"], patches["ics"]:
            from cal_scraper.cli import main

            # Run from tmp_path so file is written there
            import os

            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                result = main([])
            finally:
                os.chdir(old_cwd)

            assert result == 0
            assert (tmp_path / "moravska-galerie-deti.ics").exists()

    def test_long_output_flag(self, tmp_path):
        """main(["--output", "custom.ics"]) sets output path to custom.ics."""
        out = tmp_path / "custom.ics"
        patches = _patch_pipeline()
        with patches["fetch"], patches["extract"], patches["ics"]:
            from cal_scraper.cli import main

            result = main(["--output", str(out)])
            assert result == 0
            assert out.exists()

    def test_short_output_flag(self, tmp_path):
        """main(["-o", "custom.ics"]) sets output path to custom.ics."""
        out = tmp_path / "custom.ics"
        patches = _patch_pipeline()
        with patches["fetch"], patches["extract"], patches["ics"]:
            from cal_scraper.cli import main

            result = main(["-o", str(out)])
            assert result == 0
            assert out.exists()

    def test_verbose_flag(self, tmp_path):
        """main(["--verbose"]) enables DEBUG-level logging."""
        out = tmp_path / "out.ics"
        patches = _patch_pipeline()
        with patches["fetch"], patches["extract"], patches["ics"], \
             patch("cal_scraper.cli.logging") as mock_logging:
            from cal_scraper.cli import main

            main(["--verbose", "-o", str(out)])
            # basicConfig should be called with DEBUG level
            mock_logging.basicConfig.assert_called_once()
            args, kwargs = mock_logging.basicConfig.call_args
            assert kwargs.get("level") == 10  # logging.DEBUG == 10


# ---------------------------------------------------------------------------
# CLI-01/02: Pipeline wiring — fetch → extract → ics → write
# ---------------------------------------------------------------------------


class TestCliPipeline:
    """CLI calls the three pipeline functions in order and writes the output file."""

    def test_pipeline_call_order(self, tmp_path):
        """main() calls fetch_all_pages, extract_all_events, events_to_ics in sequence."""
        out = tmp_path / "output.ics"
        call_order = []

        def track_fetch(*a, **kw):
            call_order.append("fetch")
            return ["<html>page1</html>"]

        def track_extract(*a, **kw):
            call_order.append("extract")
            return MOCK_EVENTS

        def track_ics(*a, **kw):
            call_order.append("ics")
            return MOCK_ICS

        with patch("cal_scraper.cli.fetch_all_pages", side_effect=track_fetch), \
             patch("cal_scraper.cli.extract_all_events", side_effect=track_extract), \
             patch("cal_scraper.cli.events_to_ics", side_effect=track_ics):
            from cal_scraper.cli import main

            result = main(["-o", str(out)])

        assert call_order == ["fetch", "extract", "ics"]
        assert result == 0

    def test_output_file_contains_ics_content(self, tmp_path):
        """main() writes the ICS string returned by events_to_ics to the output file."""
        out = tmp_path / "output.ics"
        patches = _patch_pipeline()
        with patches["fetch"], patches["extract"], patches["ics"]:
            from cal_scraper.cli import main

            main(["-o", str(out)])

        assert out.read_text(encoding="utf-8") == MOCK_ICS

    def test_extract_receives_fetched_pages(self, tmp_path):
        """extract_all_events receives the pages returned by fetch_all_pages."""
        out = tmp_path / "output.ics"
        pages = ["<html>p1</html>", "<html>p2</html>"]

        with patch("cal_scraper.cli.fetch_all_pages", return_value=pages) as mock_fetch, \
             patch("cal_scraper.cli.extract_all_events", return_value=MOCK_EVENTS) as mock_extract, \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS):
            from cal_scraper.cli import main

            main(["-o", str(out)])
            mock_extract.assert_called_once_with(pages)

    def test_ics_receives_extracted_events(self, tmp_path):
        """events_to_ics receives the events returned by extract_all_events."""
        out = tmp_path / "output.ics"

        with patch("cal_scraper.cli.fetch_all_pages", return_value=["<html></html>"]), \
             patch("cal_scraper.cli.extract_all_events", return_value=MOCK_EVENTS), \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS) as mock_ics:
            from cal_scraper.cli import main

            main(["-o", str(out)])
            mock_ics.assert_called_once_with(MOCK_EVENTS)


# ---------------------------------------------------------------------------
# CLI-02: Summary output — event count, date range, output path
# ---------------------------------------------------------------------------


class TestCliSummary:
    """CLI prints event count, date range, and output path to stdout."""

    def test_summary_with_events(self, tmp_path, capsys):
        """With events: output contains event count and date range."""
        out = tmp_path / "output.ics"
        patches = _patch_pipeline()
        with patches["fetch"], patches["extract"], patches["ics"]:
            from cal_scraper.cli import main

            main(["-o", str(out)])

        captured = capsys.readouterr().out
        assert "2" in captured  # 2 events
        assert "2026-04-08" in captured  # min date
        assert "2026-07-07" in captured  # max date

    def test_summary_output_path_confirmation(self, tmp_path, capsys):
        """Output path confirmation line present in stdout."""
        out = tmp_path / "output.ics"
        patches = _patch_pipeline()
        with patches["fetch"], patches["extract"], patches["ics"]:
            from cal_scraper.cli import main

            main(["-o", str(out)])

        captured = capsys.readouterr().out
        assert str(out) in captured

    def test_summary_no_events(self, tmp_path, capsys):
        """With empty events: output contains 'No events found'."""
        out = tmp_path / "output.ics"
        patches = _patch_pipeline(events=[])
        with patches["fetch"], patches["extract"], patches["ics"]:
            from cal_scraper.cli import main

            main(["-o", str(out)])

        captured = capsys.readouterr().out
        assert "No events found" in captured


# ---------------------------------------------------------------------------
# Error handling — ScrapingError
# ---------------------------------------------------------------------------


class TestCliErrorHandling:
    """CLI handles ScrapingError from fetch_all_pages gracefully."""

    def test_scraping_error_returns_1(self, tmp_path):
        """ScrapingError results in return code 1."""
        from cal_scraper.fetcher import ScrapingError

        with patch(
            "cal_scraper.cli.fetch_all_pages",
            side_effect=ScrapingError("Failed to fetch first page"),
        ):
            from cal_scraper.cli import main

            result = main(["-o", str(tmp_path / "out.ics")])
            assert result == 1

    def test_scraping_error_prints_to_stderr(self, tmp_path, capsys):
        """ScrapingError message is printed to stderr."""
        from cal_scraper.fetcher import ScrapingError

        with patch(
            "cal_scraper.cli.fetch_all_pages",
            side_effect=ScrapingError("Network failure"),
        ):
            from cal_scraper.cli import main

            main(["-o", str(tmp_path / "out.ics")])

        captured = capsys.readouterr().err
        assert "Network failure" in captured

    def test_scraping_error_no_output_file(self, tmp_path):
        """ScrapingError means no output file is created."""
        from cal_scraper.fetcher import ScrapingError

        out = tmp_path / "out.ics"
        with patch(
            "cal_scraper.cli.fetch_all_pages",
            side_effect=ScrapingError("Boom"),
        ):
            from cal_scraper.cli import main

            main(["-o", str(out)])

        assert not out.exists()
