"""Tests for CLI entry point and multi-site pipeline wiring."""

import sys
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

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

MOCK_ICS = "BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR\n"


@pytest.fixture(autouse=True)
def _mock_hvezdarna_scrape():
    """Prevent hvezdarna from making real HTTP calls during CLI tests."""
    with patch("cal_scraper.sites.hvezdarna.scrape", return_value=MOCK_EVENTS):
        yield



# ---------------------------------------------------------------------------
# CLI-01: Argument parsing
# ---------------------------------------------------------------------------


class TestCliArgParsing:
    """CLI argument parsing for --output-dir, --site, --verbose flags."""

    def test_default_output_dir(self, tmp_path):
        """main([]) writes to current directory by default."""
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=MOCK_EVENTS), \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS):
            from cal_scraper.cli import main
            import os
            old_cwd = os.getcwd()
            os.chdir(tmp_path)
            try:
                result = main([])
            finally:
                os.chdir(old_cwd)

            assert result == 0
            assert (tmp_path / "moravska-galerie.ics").exists()

    def test_output_dir_flag(self, tmp_path):
        """main(["--output-dir", dir]) writes site files to specified directory."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=MOCK_EVENTS), \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS):
            from cal_scraper.cli import main
            result = main(["--output-dir", str(out_dir)])
            assert result == 0
            assert (out_dir / "moravska-galerie.ics").exists()

    def test_short_output_dir_flag(self, tmp_path):
        """main(["-d", dir]) works as --output-dir alias."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=MOCK_EVENTS), \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS):
            from cal_scraper.cli import main
            result = main(["-d", str(out_dir)])
            assert result == 0
            assert (out_dir / "moravska-galerie.ics").exists()

    def test_verbose_flag(self, tmp_path):
        """main(["--verbose"]) enables DEBUG-level logging."""
        import logging
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=MOCK_EVENTS), \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS), \
             patch("logging.basicConfig") as mock_basic_config:
            from cal_scraper.cli import main
            main(["--verbose", "-d", str(out_dir)])
            mock_basic_config.assert_called_once()
            _args, kwargs = mock_basic_config.call_args
            assert kwargs.get("level") == logging.DEBUG

    def test_site_flag_filters(self, tmp_path):
        """main(["--site", "moravska-galerie"]) runs only selected site."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=MOCK_EVENTS) as mock_scrape, \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS):
            from cal_scraper.cli import main
            result = main(["--site", "moravska-galerie", "-d", str(out_dir)])
            assert result == 0
            mock_scrape.assert_called_once()


# ---------------------------------------------------------------------------
# CLI-01/02: Pipeline wiring — site.scrape() → ics → write
# ---------------------------------------------------------------------------


class TestCliPipeline:
    """CLI calls site scrape and ICS generator and writes output."""

    def test_pipeline_writes_ics_content(self, tmp_path):
        """main() writes the ICS string returned by events_to_ics to the output file."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=MOCK_EVENTS), \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS):
            from cal_scraper.cli import main
            main(["-d", str(out_dir)])

        assert (out_dir / "moravska-galerie.ics").read_text(encoding="utf-8") == MOCK_ICS

    def test_ics_receives_site_config_params(self, tmp_path):
        """events_to_ics receives per-site cal_name, source_url, prodid."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=MOCK_EVENTS), \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS) as mock_ics:
            from cal_scraper.cli import main
            main(["--site", "moravska-galerie", "-d", str(out_dir)])
            mock_ics.assert_called_once()
            _, kwargs = mock_ics.call_args
            assert kwargs["cal_name"] == "Moravská galerie – Děti a rodiny (unofficial)"
            assert "moravska-galerie" in kwargs["prodid"]
            assert kwargs["source_url"] == "https://moravska-galerie.cz/program/deti-a-rodiny/"

    def test_no_details_passed_to_scrape(self, tmp_path):
        """--no-details flag is passed through to site scrape function."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=MOCK_EVENTS) as mock_scrape, \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS):
            from cal_scraper.cli import main
            main(["--no-details", "-d", str(out_dir)])
            mock_scrape.assert_called_once()
            _, kwargs = mock_scrape.call_args
            assert kwargs["no_details"] is True


# ---------------------------------------------------------------------------
# CLI-02: Summary output — event count, date range, output path
# ---------------------------------------------------------------------------


class TestCliSummary:
    """CLI prints event count, date range, and output path to stdout."""

    def test_summary_with_events(self, tmp_path, capsys):
        """With events: output contains event count and date range."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=MOCK_EVENTS), \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS):
            from cal_scraper.cli import main
            main(["-d", str(out_dir)])

        captured = capsys.readouterr().out
        assert "2" in captured  # 2 events
        assert "2026-04-08" in captured  # min date
        assert "2026-07-07" in captured  # max date

    def test_summary_output_path_confirmation(self, tmp_path, capsys):
        """Output path confirmation line present in stdout."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=MOCK_EVENTS), \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS):
            from cal_scraper.cli import main
            main(["-d", str(out_dir)])

        captured = capsys.readouterr().out
        assert "moravska-galerie.ics" in captured

    def test_summary_no_events(self, tmp_path, capsys):
        """With empty events: returns 1 and prints error to stderr."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=[]), \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS):
            from cal_scraper.cli import main
            result = main(["-d", str(out_dir)])

        assert result == 1
        captured = capsys.readouterr().err
        assert "no events found" in captured.lower()

    def test_dry_run_prints_to_stdout(self, tmp_path, capsys):
        """--dry-run prints ICS to stdout instead of writing file."""
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=MOCK_EVENTS), \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS):
            from cal_scraper.cli import main
            result = main(["--dry-run"])

        assert result == 0
        captured = capsys.readouterr().out
        assert MOCK_ICS in captured


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestCliErrorHandling:
    """CLI handles errors from site scrape functions gracefully."""

    def test_scraping_error_returns_1(self, tmp_path):
        """Exception from site scrape results in return code 1."""
        from cal_scraper.sites.moravska_galerie.fetcher import ScrapingError

        with patch(
            "cal_scraper.sites.moravska_galerie.scrape",
            side_effect=ScrapingError("Failed to fetch first page"),
        ):
            from cal_scraper.cli import main
            result = main(["-d", str(tmp_path)])
            assert result == 1

    def test_scraping_error_prints_to_stderr(self, tmp_path, capsys):
        """Exception message is printed to stderr."""
        from cal_scraper.sites.moravska_galerie.fetcher import ScrapingError

        with patch(
            "cal_scraper.sites.moravska_galerie.scrape",
            side_effect=ScrapingError("Network failure"),
        ):
            from cal_scraper.cli import main
            main(["-d", str(tmp_path)])

        captured = capsys.readouterr().err
        assert "Network failure" in captured

    def test_scraping_error_no_output_file(self, tmp_path):
        """Exception means no output file is created."""
        from cal_scraper.sites.moravska_galerie.fetcher import ScrapingError

        with patch(
            "cal_scraper.sites.moravska_galerie.scrape",
            side_effect=ScrapingError("Boom"),
        ):
            from cal_scraper.cli import main
            main(["-d", str(tmp_path)])

        assert not (tmp_path / "moravska-galerie.ics").exists()


# ---------------------------------------------------------------------------
# --no-details flag
# ---------------------------------------------------------------------------


class TestCliNoDetailsFlag:
    """CLI --no-details flag is passed to site scrape."""

    def test_no_details_flag_recognized(self, tmp_path):
        """--no-details flag is accepted without error."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=MOCK_EVENTS) as mock_scrape, \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS):
            from cal_scraper.cli import main
            result = main(["--no-details", "-d", str(out_dir)])
            assert result == 0
            _, kwargs = mock_scrape.call_args
            assert kwargs["no_details"] is True

    def test_details_by_default(self, tmp_path):
        """Without --no-details, no_details=False is passed to scrape."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        with patch("cal_scraper.sites.moravska_galerie.scrape", return_value=MOCK_EVENTS) as mock_scrape, \
             patch("cal_scraper.cli.events_to_ics", return_value=MOCK_ICS):
            from cal_scraper.cli import main
            result = main(["-d", str(out_dir)])
            assert result == 0
            _, kwargs = mock_scrape.call_args
            assert kwargs["no_details"] is False
