"""Tests for cal_scraper.sites.hvezdarna.fetcher — week-based page fetching."""

from datetime import date, datetime
from unittest.mock import patch

import pytest
import requests
import responses

from cal_scraper.sites.hvezdarna.fetcher import (
    ScrapingError,
    _monday_of,
    _parse_max_timestamp,
    _week_url,
    fetch_all_weeks,
    fetch_page,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

BASE_URL = "https://www.hvezdarna.cz/"

# kalendarInit(current, min, max, ...) — max is 2026-06-30 00:00 UTC = 1782518400
# We use a realistic timestamp for the max date.
MAX_TS = int(datetime(2026, 6, 30).timestamp())

PAGE_HTML_TEMPLATE = (
    "<html><body>"
    "<script>kalendarInit(1000000, 900000, {max_ts}, 'cs')</script>"
    "<h1 class='main-program-datum'>Pondělí 1. června</h1>"
    "<div class='main-program-porad'>"
    "<h2 class='main-program-cas'>10:00</h2>"
    "<h3 class='main-program-title'>Test Show</h3>"
    "</div>"
    "</body></html>"
)

PAGE_HTML = PAGE_HTML_TEMPLATE.format(max_ts=MAX_TS)

PAGE_HTML_NO_INIT = (
    "<html><body>"
    "<h1 class='main-program-datum'>Pondělí 1. června</h1>"
    "</body></html>"
)


# ---------------------------------------------------------------------------
# _week_url tests
# ---------------------------------------------------------------------------


class TestWeekUrl:
    def test_url_format_no_zero_padding(self):
        """URL uses single-digit month/day (no zero-padding)."""
        d = date(2026, 4, 5)
        url = _week_url(BASE_URL, d)
        assert url == "https://www.hvezdarna.cz/?type=tyden&datum=2026-4-5"

    def test_url_format_two_digit(self):
        """Two-digit month/day are used as-is."""
        d = date(2026, 12, 15)
        url = _week_url(BASE_URL, d)
        assert url == "https://www.hvezdarna.cz/?type=tyden&datum=2026-12-15"


# ---------------------------------------------------------------------------
# _monday_of tests
# ---------------------------------------------------------------------------


class TestMondayOf:
    def test_monday_stays(self):
        """A Monday returns itself."""
        assert _monday_of(date(2026, 4, 6)) == date(2026, 4, 6)  # Monday

    def test_wednesday(self):
        """A Wednesday returns the preceding Monday."""
        assert _monday_of(date(2026, 4, 8)) == date(2026, 4, 6)

    def test_sunday(self):
        """A Sunday returns the preceding Monday."""
        assert _monday_of(date(2026, 4, 12)) == date(2026, 4, 6)


# ---------------------------------------------------------------------------
# _parse_max_timestamp tests
# ---------------------------------------------------------------------------


class TestParseMaxTimestamp:
    def test_normal(self):
        """Extracts the third numeric argument from kalendarInit(...)."""
        html = "<script>kalendarInit(100, 200, 1782518400, 'cs')</script>"
        assert _parse_max_timestamp(html) == 1782518400

    def test_with_spaces(self):
        """Handles whitespace in the JS call."""
        html = "<script>kalendarInit( 100 , 200 , 1782518400 , 'cs' )</script>"
        assert _parse_max_timestamp(html) == 1782518400

    def test_missing(self):
        """Returns None when kalendarInit is not found."""
        html = "<html><body>nothing here</body></html>"
        assert _parse_max_timestamp(html) is None


# ---------------------------------------------------------------------------
# fetch_page tests
# ---------------------------------------------------------------------------


class TestFetchPage:
    @responses.activate
    def test_success(self):
        """Successful 200 response returns HTML."""
        url = "https://www.hvezdarna.cz/?type=tyden&datum=2026-4-6"
        responses.add(responses.GET, url, body="<html>OK</html>", status=200)
        result = fetch_page(url, requests.Session())
        assert result == "<html>OK</html>"

    @responses.activate
    def test_failure_returns_none(self):
        """Network error returns None."""
        url = "https://www.hvezdarna.cz/?type=tyden&datum=2026-4-6"
        responses.add(
            responses.GET, url, body=requests.exceptions.Timeout("timed out")
        )
        result = fetch_page(url, requests.Session())
        assert result is None


# ---------------------------------------------------------------------------
# fetch_all_weeks tests
# ---------------------------------------------------------------------------


class TestFetchAllWeeks:
    @responses.activate
    @patch("cal_scraper.sites.hvezdarna.fetcher.date")
    @patch("cal_scraper.sites.hvezdarna.fetcher.time.sleep")
    def test_fetches_correct_weeks(self, mock_sleep, mock_date):
        """Fetches week-by-week from current Monday to max date."""
        # Pin "today" to a Wednesday 2026-06-17 → Monday is 2026-06-15
        mock_date.today.return_value = date(2026, 6, 17)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        # Max date = 2026-06-30 → need weeks starting 6/15, 6/22, 6/29
        max_ts = int(datetime(2026, 6, 30).timestamp())
        page_html = (
            "<html><script>kalendarInit(1, 1, {ts}, 'cs')</script></html>"
        ).format(ts=max_ts)

        # Use a catch-all matcher for all GET requests to the base
        responses.add(
            responses.GET,
            "https://www.hvezdarna.cz/",
            body=page_html,
            status=200,
        )

        pages = fetch_all_weeks(BASE_URL)
        # Should have 3 weeks: 6/15, 6/22, 6/29
        assert len(pages) == 3
        assert pages[0][1] == date(2026, 6, 15)
        assert pages[1][1] == date(2026, 6, 22)
        assert pages[2][1] == date(2026, 6, 29)

        # Sleep called between page fetches (not before first)
        assert mock_sleep.call_count == 2

    @responses.activate
    @patch("cal_scraper.sites.hvezdarna.fetcher.date")
    def test_first_page_failure_raises(self, mock_date):
        """Raises ScrapingError when first page fails."""
        mock_date.today.return_value = date(2026, 6, 17)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        responses.add(
            responses.GET,
            "https://www.hvezdarna.cz/",
            body=requests.exceptions.ConnectionError("refused"),
        )

        with pytest.raises(ScrapingError):
            fetch_all_weeks(BASE_URL)

    @responses.activate
    @patch("cal_scraper.sites.hvezdarna.fetcher.date")
    def test_no_kalendar_init_returns_single_page(self, mock_date):
        """Without kalendarInit, returns only the current week."""
        mock_date.today.return_value = date(2026, 6, 17)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        responses.add(
            responses.GET,
            "https://www.hvezdarna.cz/",
            body=PAGE_HTML_NO_INIT,
            status=200,
        )

        pages = fetch_all_weeks(BASE_URL)
        assert len(pages) == 1
        assert pages[0][1] == date(2026, 6, 15)

    @responses.activate
    @patch("cal_scraper.sites.hvezdarna.fetcher.date")
    @patch("cal_scraper.sites.hvezdarna.fetcher.time.sleep")
    def test_user_agent(self, mock_sleep, mock_date):
        """Requests include a User-Agent containing 'cal-scraper'."""
        mock_date.today.return_value = date(2026, 6, 17)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        max_ts = int(datetime(2026, 6, 18).timestamp())
        page_html = (
            "<html><script>kalendarInit(1, 1, {ts}, 'cs')</script></html>"
        ).format(ts=max_ts)

        responses.add(
            responses.GET,
            "https://www.hvezdarna.cz/",
            body=page_html,
            status=200,
        )

        fetch_all_weeks(BASE_URL)
        assert "cal-scraper" in responses.calls[0].request.headers["User-Agent"]
