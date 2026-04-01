"""Tests for cal_scraper.fetcher — HTTP page fetching with pagination discovery."""

import pytest
import requests
import responses
from unittest.mock import patch

from cal_scraper.fetcher import (
    fetch_all_pages,
    fetch_page,
    _get_page_url,
    _discover_max_pages,
    ScrapingError,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

BASE_URL = "https://example.com/events/"

PAGE1_HTML = (
    '<html><body>'
    '<div class="ecs-posts" data-settings=\'{"max_num_pages":3}\'>'
    '<article class="elementor-post post-100">event 1</article>'
    '</div></body></html>'
)

PAGE2_HTML = (
    '<html><body>'
    '<div class="ecs-posts">'
    '<article class="elementor-post post-200">event 2</article>'
    '</div></body></html>'
)

PAGE3_HTML = (
    '<html><body>'
    '<div class="ecs-posts">'
    '<article class="elementor-post post-300">event 3</article>'
    '</div></body></html>'
)


# ---------------------------------------------------------------------------
# _get_page_url tests
# ---------------------------------------------------------------------------

class TestGetPageUrl:
    def test_get_page_url_page_one(self):
        """Page 1 returns base URL unchanged."""
        assert _get_page_url(BASE_URL, 1) == BASE_URL

    def test_get_page_url_page_n(self):
        """Page N (N>=2) appends page/{N}/ to base URL."""
        assert _get_page_url(BASE_URL, 3) == "https://example.com/events/page/3/"


# ---------------------------------------------------------------------------
# _discover_max_pages tests
# ---------------------------------------------------------------------------

class TestDiscoverMaxPages:
    def test_discover_max_pages(self):
        """HTML with data-settings containing max_num_pages returns that value."""
        html = '<html><body><div class="ecs-posts" data-settings=\'{"max_num_pages":3}\'></div></body></html>'
        assert _discover_max_pages(html) == 3

    def test_discover_max_pages_missing_attr(self):
        """HTML with div.ecs-posts but no data-settings attribute returns 1."""
        html = '<html><body><div class="ecs-posts"></div></body></html>'
        assert _discover_max_pages(html) == 1

    def test_discover_max_pages_missing_container(self):
        """HTML without div.ecs-posts returns 1."""
        html = "<html><body><div>no posts here</div></body></html>"
        assert _discover_max_pages(html) == 1


# ---------------------------------------------------------------------------
# fetch_page tests
# ---------------------------------------------------------------------------

class TestFetchPage:
    @responses.activate
    def test_fetch_page_success(self):
        """Successful 200 response returns the HTML body string."""
        url = "https://example.com/events/"
        responses.add(responses.GET, url, body="<html>OK</html>", status=200)

        result = fetch_page(url, requests.Session())
        assert result == "<html>OK</html>"

    @responses.activate
    def test_fetch_page_timeout(self):
        """Timeout exception returns None and logs a warning."""
        url = "https://example.com/events/"
        responses.add(
            responses.GET, url, body=requests.exceptions.Timeout("timed out")
        )

        result = fetch_page(url, requests.Session())
        assert result is None

    @responses.activate
    def test_fetch_page_connection_error(self):
        """ConnectionError returns None and logs a warning."""
        url = "https://example.com/events/"
        responses.add(
            responses.GET, url, body=requests.exceptions.ConnectionError("refused")
        )

        result = fetch_page(url, requests.Session())
        assert result is None


# ---------------------------------------------------------------------------
# fetch_all_pages tests
# ---------------------------------------------------------------------------

class TestFetchAllPages:
    @responses.activate
    def test_fetch_all_pages_success(self):
        """Mocked 3 pages with data-settings max=3 returns list of 3 HTML strings."""
        responses.add(responses.GET, BASE_URL, body=PAGE1_HTML, status=200)
        responses.add(
            responses.GET, BASE_URL + "page/2/", body=PAGE2_HTML, status=200
        )
        responses.add(
            responses.GET, BASE_URL + "page/3/", body=PAGE3_HTML, status=200
        )

        pages = fetch_all_pages(BASE_URL)
        assert len(pages) == 3
        assert "event 1" in pages[0]
        assert "event 2" in pages[1]
        assert "event 3" in pages[2]

    @responses.activate
    def test_fetch_all_pages_user_agent(self):
        """Requests include a User-Agent header containing 'cal-scraper'."""
        responses.add(responses.GET, BASE_URL, body=PAGE1_HTML, status=200)
        responses.add(
            responses.GET, BASE_URL + "page/2/", body=PAGE2_HTML, status=200
        )
        responses.add(
            responses.GET, BASE_URL + "page/3/", body=PAGE3_HTML, status=200
        )

        fetch_all_pages(BASE_URL)
        assert "cal-scraper" in responses.calls[0].request.headers["User-Agent"]

    @responses.activate
    @patch("cal_scraper.fetcher.time.sleep")
    def test_fetch_all_pages_delay(self, mock_sleep):
        """time.sleep(1.0) is called between page fetches (not before the first)."""
        responses.add(responses.GET, BASE_URL, body=PAGE1_HTML, status=200)
        responses.add(
            responses.GET, BASE_URL + "page/2/", body=PAGE2_HTML, status=200
        )
        responses.add(
            responses.GET, BASE_URL + "page/3/", body=PAGE3_HTML, status=200
        )

        fetch_all_pages(BASE_URL)
        # 3 pages → sleep called before page 2 and page 3 = 2 calls
        assert mock_sleep.call_count >= 2
        mock_sleep.assert_any_call(1.0)

    @responses.activate
    def test_fetch_all_pages_partial_failure(self):
        """1 of 3 pages fails → returns 2 HTML strings, logs warning."""
        responses.add(responses.GET, BASE_URL, body=PAGE1_HTML, status=200)
        responses.add(
            responses.GET,
            BASE_URL + "page/2/",
            body=requests.exceptions.ConnectionError("refused"),
        )
        responses.add(
            responses.GET, BASE_URL + "page/3/", body=PAGE3_HTML, status=200
        )

        pages = fetch_all_pages(BASE_URL)
        assert len(pages) == 2
        assert "event 1" in pages[0]
        assert "event 3" in pages[1]

    @responses.activate
    def test_fetch_all_pages_majority_failure(self):
        """2 of 3 pages fail → raises ScrapingError."""
        responses.add(responses.GET, BASE_URL, body=PAGE1_HTML, status=200)
        responses.add(
            responses.GET,
            BASE_URL + "page/2/",
            body=requests.exceptions.ConnectionError("refused"),
        )
        responses.add(
            responses.GET,
            BASE_URL + "page/3/",
            body=requests.exceptions.Timeout("timed out"),
        )

        with pytest.raises(ScrapingError):
            fetch_all_pages(BASE_URL)
