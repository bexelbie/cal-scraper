"""Shared HTTP client with optional CORS proxy fallback.

When the ``CORS_PROXY_URL`` environment variable is set and a direct request
fails with a timeout or connection error, the client retries the request
through the specified CORS proxy.  The proxy is only attempted for HTTPS
URLs (the proxy rejects plain HTTP).

Exports:
    fetch — fetch a URL with optional proxy fallback
"""

from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30  # seconds


def _get_proxy_url() -> str | None:
    """Return the CORS proxy URL from environment, or None if unset."""
    return os.environ.get("CORS_PROXY_URL") or None


def _is_proxy_eligible(url: str) -> bool:
    """Check if a URL can be routed through the proxy (HTTPS only)."""
    return url.lower().startswith("https://")


def _fetch_via_proxy(
    proxy_url: str,
    target_url: str,
    timeout: int | float,
) -> requests.Response:
    """POST to the CORS proxy and return the upstream response."""
    logger.info("Retrying via CORS proxy: %s", target_url)
    return requests.post(proxy_url, json={"url": target_url}, timeout=timeout)


def fetch(
    url: str,
    *,
    session: requests.Session | None = None,
    timeout: int | float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
) -> requests.Response:
    """Fetch a URL, falling back to a CORS proxy on network failure.

    1. Tries a direct ``GET`` via *session* (or ``requests.get``).
    2. On :class:`~requests.exceptions.Timeout` or
       :class:`~requests.exceptions.ConnectionError` — **and** the
       ``CORS_PROXY_URL`` env-var is set **and** *url* is HTTPS —
       retries the request through the proxy.
    3. All other exceptions propagate unchanged.

    The caller is responsible for calling ``response.raise_for_status()``
    if it wants to treat HTTP 4xx/5xx as errors.

    Parameters
    ----------
    url : str
        The URL to fetch.
    session : requests.Session | None
        Optional session (headers, cookies pre-configured).
    timeout : int | float
        Per-attempt timeout in seconds (applies to both direct and proxy).
    headers : dict[str, str] | None
        Extra headers for the direct request when *session* is ``None``.
        When *session* is provided, these are merged per ``requests``
        semantics (per-request headers win on conflict).
    """
    kwargs: dict = {"timeout": timeout}
    if headers:
        kwargs["headers"] = headers

    client = session if session is not None else requests

    try:
        return client.get(url, **kwargs)  # type: ignore[union-attr]
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as direct_err:
        proxy_url = _get_proxy_url()
        if proxy_url and _is_proxy_eligible(url):
            try:
                return _fetch_via_proxy(proxy_url, url, timeout)
            except requests.RequestException as proxy_err:
                logger.warning("CORS proxy also failed for %s: %s", url, proxy_err)
        raise direct_err
