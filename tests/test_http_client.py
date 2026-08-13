"""Tests for cal_scraper.http_client — proxy fallback logic."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from cal_scraper.http_client import fetch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok_response(text: str = "OK") -> MagicMock:
    """Build a fake successful Response."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = 200
    resp.text = text
    return resp


# ---------------------------------------------------------------------------
# Direct request succeeds — no proxy involved
# ---------------------------------------------------------------------------


class TestDirectSuccess:
    """Proxy should never be contacted when the direct request works."""

    @patch("cal_scraper.http_client.requests")
    def test_returns_response(self, mock_requests):
        mock_requests.get.return_value = _ok_response("hello")
        resp = fetch("https://example.com")
        assert resp.text == "hello"
        mock_requests.get.assert_called_once()

    @patch("cal_scraper.http_client.requests")
    def test_passes_timeout_and_headers(self, mock_requests):
        mock_requests.get.return_value = _ok_response()
        fetch("https://example.com", timeout=10, headers={"X-Foo": "bar"})
        mock_requests.get.assert_called_once_with(
            "https://example.com", timeout=10, verify=True, headers={"X-Foo": "bar"}
        )

    @patch("cal_scraper.http_client.requests")
    def test_uses_session_when_provided(self, mock_requests):
        session = MagicMock(spec=requests.Session)
        session.get.return_value = _ok_response("via-session")
        resp = fetch("https://example.com", session=session)
        assert resp.text == "via-session"
        session.get.assert_called_once()
        mock_requests.get.assert_not_called()


# ---------------------------------------------------------------------------
# Timeout → proxy fallback
# ---------------------------------------------------------------------------


class TestProxyFallback:
    """When direct request times out, proxy is attempted if configured."""

    @patch.dict("os.environ", {"FALLBACK_PROXY_URL": "http://proxy.test:8888"})
    @patch("cal_scraper.http_client.requests")
    def test_timeout_triggers_proxy(self, mock_requests):
        mock_requests.exceptions = requests.exceptions
        mock_requests.get.side_effect = [
            requests.exceptions.Timeout("timed out"),
            _ok_response("from proxy"),
        ]

        resp = fetch("https://blocked.example.com", timeout=5)
        assert resp.text == "from proxy"
        assert mock_requests.get.call_args_list == [
            (("https://blocked.example.com",), {"timeout": 5, "verify": True}),
            (("https://blocked.example.com",), {
                "timeout": 5,
                "verify": True,
                "proxies": {
                    "http": "http://proxy.test:8888",
                    "https": "http://proxy.test:8888",
                },
            }),
        ]

    @patch.dict("os.environ", {"FALLBACK_PROXY_URL": "https://proxy.test:8888"})
    @patch("cal_scraper.http_client.requests")
    def test_https_proxy_url_is_supported(self, mock_requests):
        mock_requests.exceptions = requests.exceptions
        mock_requests.get.side_effect = [
            requests.exceptions.ConnectionError("refused"),
            _ok_response("from proxy"),
        ]

        resp = fetch("http://blocked.example.com")
        assert resp.text == "from proxy"
        assert mock_requests.get.call_args_list[1] == (
            ("http://blocked.example.com",), {
                "timeout": 30,
                "verify": True,
                "proxies": {
                    "http": "https://proxy.test:8888",
                    "https": "https://proxy.test:8888",
                },
            },
        )

    @patch.dict("os.environ", {"FALLBACK_PROXY_URL": "http://proxy.test:8888"})
    @patch("cal_scraper.http_client.requests")
    def test_connection_error_triggers_proxy(self, mock_requests):
        mock_requests.exceptions = requests.exceptions
        mock_requests.get.side_effect = [
            requests.exceptions.ConnectionError("refused"),
            _ok_response("from proxy"),
        ]

        resp = fetch("https://blocked.example.com")
        assert resp.text == "from proxy"

    @patch.dict("os.environ", {"FALLBACK_PROXY_URL": "http://proxy.test:8888"})
    @patch("cal_scraper.http_client.requests")
    def test_proxy_also_fails_raises_original_error(self, mock_requests):
        mock_requests.exceptions = requests.exceptions
        mock_requests.RequestException = requests.RequestException
        original = requests.exceptions.Timeout("direct timed out")
        mock_requests.get.side_effect = [
            original,
            requests.exceptions.ConnectionError("proxy down"),
        ]

        with pytest.raises(requests.exceptions.Timeout) as exc_info:
            fetch("https://blocked.example.com")
        assert exc_info.value is original


# ---------------------------------------------------------------------------
# Proxy NOT attempted
# ---------------------------------------------------------------------------


class TestProxyNotAttempted:
    """Proxy must be skipped when not configured or the direct request succeeds."""

    @patch.dict("os.environ", {}, clear=True)
    @patch("cal_scraper.http_client.requests")
    def test_no_env_var_raises_directly(self, mock_requests):
        mock_requests.exceptions = requests.exceptions
        mock_requests.get.side_effect = requests.exceptions.Timeout("timed out")

        with pytest.raises(requests.exceptions.Timeout):
            fetch("https://example.com")
        assert mock_requests.get.call_count == 1

    @patch.dict("os.environ", {"FALLBACK_PROXY_URL": "http://proxy.test:8888"})
    @patch("cal_scraper.http_client.requests")
    def test_http_error_does_not_trigger_proxy(self, mock_requests):
        """HTTP 500 is not a network failure — don't fall back."""
        mock_requests.exceptions = requests.exceptions
        bad_resp = MagicMock(spec=requests.Response)
        bad_resp.status_code = 500
        mock_requests.get.return_value = bad_resp

        resp = fetch("https://example.com")
        assert resp.status_code == 500
        mock_requests.get.assert_called_once()

    @patch.dict("os.environ", {"FALLBACK_PROXY_URL": ""})
    @patch("cal_scraper.http_client.requests")
    def test_empty_env_var_skips_proxy(self, mock_requests):
        """Empty string should be treated as unset."""
        mock_requests.exceptions = requests.exceptions
        mock_requests.get.side_effect = requests.exceptions.Timeout("timed out")

        with pytest.raises(requests.exceptions.Timeout):
            fetch("https://example.com")
        assert mock_requests.get.call_count == 1


# ---------------------------------------------------------------------------
# Session + proxy interaction
# ---------------------------------------------------------------------------


class TestSessionWithProxy:
    """Proxy fallback works correctly when a session is provided."""

    @patch.dict("os.environ", {"FALLBACK_PROXY_URL": "http://proxy.test:8888"})
    @patch("cal_scraper.http_client.requests")
    def test_session_timeout_falls_back_to_proxy(self, mock_requests):
        mock_requests.exceptions = requests.exceptions

        session = MagicMock(spec=requests.Session)
        session.get.side_effect = [
            requests.exceptions.Timeout("session timed out"),
            _ok_response("proxy win"),
        ]

        resp = fetch("https://blocked.example.com", session=session)
        assert resp.text == "proxy win"
        assert session.get.call_count == 2
        assert session.get.call_args_list[1].kwargs["proxies"] == {
            "http": "http://proxy.test:8888",
            "https": "http://proxy.test:8888",
        }
