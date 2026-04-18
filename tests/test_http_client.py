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
            "https://example.com", timeout=10, headers={"X-Foo": "bar"}
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

    @patch.dict("os.environ", {"CORS_PROXY_URL": "https://proxy.test/api"})
    @patch("cal_scraper.http_client.requests")
    def test_timeout_triggers_proxy(self, mock_requests):
        mock_requests.exceptions = requests.exceptions
        mock_requests.get.side_effect = requests.exceptions.Timeout("timed out")
        mock_requests.post.return_value = _ok_response("from proxy")

        resp = fetch("https://blocked.example.com", timeout=5)
        assert resp.text == "from proxy"
        mock_requests.post.assert_called_once_with(
            "https://proxy.test/api",
            json={"url": "https://blocked.example.com"},
            timeout=5,
        )

    @patch.dict("os.environ", {"CORS_PROXY_URL": "https://proxy.test/api"})
    @patch("cal_scraper.http_client.requests")
    def test_connection_error_triggers_proxy(self, mock_requests):
        mock_requests.exceptions = requests.exceptions
        mock_requests.get.side_effect = requests.exceptions.ConnectionError("refused")
        mock_requests.post.return_value = _ok_response("from proxy")

        resp = fetch("https://blocked.example.com")
        assert resp.text == "from proxy"

    @patch.dict("os.environ", {"CORS_PROXY_URL": "https://proxy.test/api"})
    @patch("cal_scraper.http_client.requests")
    def test_proxy_also_fails_raises_original_error(self, mock_requests):
        mock_requests.exceptions = requests.exceptions
        mock_requests.RequestException = requests.RequestException
        original = requests.exceptions.Timeout("direct timed out")
        mock_requests.get.side_effect = original
        mock_requests.post.side_effect = requests.exceptions.ConnectionError("proxy down")

        with pytest.raises(requests.exceptions.Timeout) as exc_info:
            fetch("https://blocked.example.com")
        assert exc_info.value is original


# ---------------------------------------------------------------------------
# Proxy NOT attempted
# ---------------------------------------------------------------------------


class TestProxyNotAttempted:
    """Proxy must be skipped when not configured or not eligible."""

    @patch.dict("os.environ", {}, clear=True)
    @patch("cal_scraper.http_client.requests")
    def test_no_env_var_raises_directly(self, mock_requests):
        mock_requests.exceptions = requests.exceptions
        mock_requests.get.side_effect = requests.exceptions.Timeout("timed out")

        with pytest.raises(requests.exceptions.Timeout):
            fetch("https://example.com")
        mock_requests.post.assert_not_called()

    @patch.dict("os.environ", {"CORS_PROXY_URL": "https://proxy.test/api"})
    @patch("cal_scraper.http_client.requests")
    def test_http_url_skips_proxy(self, mock_requests):
        """Proxy only accepts HTTPS — skip for plain HTTP URLs."""
        mock_requests.exceptions = requests.exceptions
        mock_requests.get.side_effect = requests.exceptions.Timeout("timed out")

        with pytest.raises(requests.exceptions.Timeout):
            fetch("http://plaintext.example.com")
        mock_requests.post.assert_not_called()

    @patch.dict("os.environ", {"CORS_PROXY_URL": "https://proxy.test/api"})
    @patch("cal_scraper.http_client.requests")
    def test_http_error_does_not_trigger_proxy(self, mock_requests):
        """HTTP 500 is not a network failure — don't fall back."""
        mock_requests.exceptions = requests.exceptions
        bad_resp = MagicMock(spec=requests.Response)
        bad_resp.status_code = 500
        mock_requests.get.return_value = bad_resp

        resp = fetch("https://example.com")
        assert resp.status_code == 500
        mock_requests.post.assert_not_called()

    @patch.dict("os.environ", {"CORS_PROXY_URL": ""})
    @patch("cal_scraper.http_client.requests")
    def test_empty_env_var_skips_proxy(self, mock_requests):
        """Empty string should be treated as unset."""
        mock_requests.exceptions = requests.exceptions
        mock_requests.get.side_effect = requests.exceptions.Timeout("timed out")

        with pytest.raises(requests.exceptions.Timeout):
            fetch("https://example.com")
        mock_requests.post.assert_not_called()


# ---------------------------------------------------------------------------
# Session + proxy interaction
# ---------------------------------------------------------------------------


class TestSessionWithProxy:
    """Proxy fallback works correctly when a session is provided."""

    @patch.dict("os.environ", {"CORS_PROXY_URL": "https://proxy.test/api"})
    @patch("cal_scraper.http_client.requests")
    def test_session_timeout_falls_back_to_proxy(self, mock_requests):
        mock_requests.exceptions = requests.exceptions
        mock_requests.post.return_value = _ok_response("proxy win")

        session = MagicMock(spec=requests.Session)
        session.get.side_effect = requests.exceptions.Timeout("session timed out")

        resp = fetch("https://blocked.example.com", session=session)
        assert resp.text == "proxy win"
        session.get.assert_called_once()
        # Proxy uses requests.post directly, not the session
        mock_requests.post.assert_called_once()
