"""Event fetcher for IKEA Brno store events API."""

from __future__ import annotations

import logging

from cal_scraper.http_client import fetch

logger = logging.getLogger(__name__)

API_URL = (
    "https://customer.prod.store-events.ingka.com/api/v1.0/events"
    "?countryCode=cz&storeNo=sto278&status=ACTIVE"
)
REQUEST_TIMEOUT = 30


def fetch_events(verbose: bool = False) -> list[dict]:
    """Fetch active events from the IKEA Brno store events API.

    Returns a list of event dicts from the JSON response.
    Raises on non-200 HTTP status.
    """
    headers = {"REQUEST-ORIGIN": "iert-customer-fe"}
    response = fetch(API_URL, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    events = response.json()
    if verbose:
        logger.info("Fetched %d events from IKEA API", len(events))

    return events
