"""Shared HTTP client with optional forward proxy fallback.

When the ``FALLBACK_PROXY_URL`` environment variable is set and a direct
request fails with a timeout or connection error, the client retries the
request through the specified forward proxy.

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
    """Return the fallback proxy URL from environment, or None if unset."""
    return os.environ.get("FALLBACK_PROXY_URL") or None


def fetch(
    url: str,
    *,
    session: requests.Session | None = None,
    timeout: int | float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    verify: bool = True,
) -> requests.Response:
    """Fetch a URL, falling back to a forward proxy on network failure.

    1. Tries a direct ``GET`` via *session* (or ``requests.get``).
    2. On :class:`~requests.exceptions.Timeout` or
       :class:`~requests.exceptions.ConnectionError` — and the
       ``FALLBACK_PROXY_URL`` env-var is set — retries through the proxy.
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
    kwargs: dict = {"timeout": timeout, "verify": verify}
    if headers:
        kwargs["headers"] = headers

    client = session if session is not None else requests

    try:
        return client.get(url, **kwargs)  # type: ignore[union-attr]
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as direct_err:
        proxy_url = _get_proxy_url()
        if proxy_url:
            try:
                logger.info("Retrying via fallback proxy: %s", url)
                return client.get(
                    url,
                    **kwargs,
                    proxies={"http": proxy_url, "https": proxy_url},
                )
            except requests.RequestException as proxy_err:
                logger.warning("Fallback proxy also failed for %s: %s", url, proxy_err)
        raise direct_err
