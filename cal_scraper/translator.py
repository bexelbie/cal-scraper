"""Translate events from Czech to English using Azure OpenAI.

Produces bilingual Event objects with:
- Title: "English / Czech"
- Description: English text → details → Czech text

Public API:
    load_azure_config()           — load config from env vars
    translate_events(events, cfg) — returns new Events with bilingual content
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import replace

import requests as http_requests

from cal_scraper.models import Event

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_ENV_MAP = {
    "azure_openai_endpoint": "AZURE_OPENAI_ENDPOINT",
    "azure_openai_key": "AZURE_OPENAI_KEY",
    "azure_openai_deployment": "AZURE_OPENAI_DEPLOYMENT",
    "azure_openai_api_version": "AZURE_OPENAI_API_VERSION",
}

REQUIRED_KEYS = list(_ENV_MAP.keys())


class TranslationError(RuntimeError):
    """Raised when Azure OpenAI is unavailable or misconfigured."""


def load_azure_config() -> dict[str, str]:
    """Load Azure OpenAI configuration from environment variables.

    Returns a dict with keys: azure_openai_endpoint, azure_openai_key,
    azure_openai_deployment, azure_openai_api_version.

    Raises TranslationError if any required variable is missing.
    """
    config: dict[str, str] = {}
    missing: list[str] = []
    for key, env_var in _ENV_MAP.items():
        val = os.environ.get(env_var, "")
        if not val:
            missing.append(env_var)
        config[key] = val

    if missing:
        raise TranslationError(
            f"Translation requires environment variables: {', '.join(missing)}"
        )
    return config


# ---------------------------------------------------------------------------
# Azure OpenAI client
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You translate Czech cultural event information to English.

Context: These are events from cultural venues in Brno, Czech Republic \
(museums, planetariums, science centers, stores). The audience is \
English-speaking parents looking for kids/family activities.

Rules:
- Translate title and description naturally
- Keep all proper nouns unchanged (venue names, Czech place names, \
personal names)
- Keep all dates, times, numbers, prices, and URLs unchanged
- Keep Czech diacritics on proper nouns (e.g. Hvězdárna, Moravská galerie)
- If text is already in English, return it unchanged
- Output valid JSON only — no commentary, no markdown fences"""


def _call_azure_openai(
    config: dict[str, str],
    messages: list[dict],
    max_tokens: int | None = None,
) -> dict:
    """Send a chat completion request to Azure OpenAI.

    Returns the parsed response body. Raises TranslationError on errors.
    """
    endpoint = config["azure_openai_endpoint"].rstrip("/")
    deployment = config["azure_openai_deployment"]
    api_version = config["azure_openai_api_version"]
    url = (
        f"{endpoint}/openai/deployments/{deployment}"
        f"/chat/completions?api-version={api_version}"
    )

    payload: dict = {"messages": messages}
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    try:
        resp = http_requests.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "api-key": config["azure_openai_key"],
            },
            timeout=120,
        )
    except http_requests.RequestException as exc:
        raise TranslationError(f"Azure OpenAI request failed: {exc}") from exc

    if resp.status_code == 404:
        raise TranslationError(
            f"Azure OpenAI deployment '{deployment}' not found. "
            "The model may have been retired."
        )
    if resp.status_code == 401:
        raise TranslationError(
            "Azure OpenAI authentication failed. Check AZURE_OPENAI_KEY."
        )
    if not (200 <= resp.status_code < 300):
        try:
            err = resp.json().get("error", {}).get("message", resp.text[:200])
        except Exception:
            err = resp.text[:200]
        raise TranslationError(f"Azure OpenAI HTTP {resp.status_code}: {err}")

    return resp.json()


# ---------------------------------------------------------------------------
# Batch translation
# ---------------------------------------------------------------------------


def _build_translation_request(events: list[Event]) -> list[dict]:
    """Build a JSON-serialisable list of {id, title, description} for the LLM."""
    items = []
    for i, ev in enumerate(events):
        items.append({
            "id": i,
            "title": ev.title,
            "description": ev.description,
        })
    return items


def _parse_translation_response(raw: str, count: int) -> list[dict]:
    """Parse the LLM's JSON array response.

    Returns a list of {id, title, description} dicts.
    Falls back to empty list on parse failure.
    """
    # Strip markdown fences if the model wraps output
    text = raw.strip()
    if text.startswith("```"):
        # Remove opening fence (```json or ```)
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3].rstrip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Translation response is not valid JSON")
        return []

    if not isinstance(parsed, list) or len(parsed) != count:
        logger.warning(
            "Translation returned %d items, expected %d",
            len(parsed) if isinstance(parsed, list) else 0,
            count,
        )
        return []

    return parsed


def _build_bilingual_description(
    english_desc: str,
    czech_desc: str,
    event: Event,
    estimated_dur_str: str,
) -> str:
    """Compose the bilingual description with details sandwiched."""
    parts: list[str] = []

    # English description (if non-empty)
    if english_desc.strip():
        parts.append(english_desc.strip())

    # --- details block ---
    detail_lines: list[str] = []
    if event.sold_out:
        detail_lines.append("[VYPRODÁNO / SOLD OUT]")
    if event.price:
        detail_lines.append(f"Price/Cena: {event.price}")
    if event.reservation:
        detail_lines.append(f"Reservation: {event.reservation}")
    if event.estimated_end and estimated_dur_str:
        detail_lines.append(
            f"Note: End time is approximate (duration estimated at {estimated_dur_str})"
        )
    detail_lines.append(f"Datum: {event.raw_date}")

    parts.append("---")
    parts.append("\n".join(detail_lines))
    parts.append("---")

    # Czech description (if non-empty)
    if czech_desc.strip():
        parts.append(czech_desc.strip())

    return "\n\n".join(parts)


def _format_duration(event: Event) -> str:
    """Format estimated duration string for an event, or empty if not estimated."""
    if not event.estimated_end or event.dtend is None:
        return ""
    from datetime import date as date_type

    if isinstance(event.dtstart, date_type) and not hasattr(event.dtstart, "hour"):
        return ""
    duration = event.dtend - event.dtstart
    total_min = int(duration.total_seconds() // 60)
    hours, mins = divmod(total_min, 60)
    if mins == 0:
        return f"{hours}h"
    if hours == 0:
        return f"{mins}min"
    return f"{hours}h {mins}min"


def translate_events(
    events: list[Event],
    config: dict[str, str],
) -> list[Event]:
    """Translate a list of events to bilingual English/Czech.

    Returns new Event objects with bilingual titles and descriptions.
    On translation failure, returns the original events unchanged.
    """
    if not events:
        return events

    items = _build_translation_request(events)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Translate each item's title and description from Czech to English. "
                "Return a JSON array with the same structure: "
                '[{"id": 0, "title": "...", "description": "..."}, ...]\n\n'
                + json.dumps(items, ensure_ascii=False)
            ),
        },
    ]

    try:
        resp = _call_azure_openai(config, messages)
        content = resp["choices"][0]["message"]["content"]
    except (TranslationError, KeyError, IndexError) as exc:
        logger.warning("Translation failed: %s — using Czech originals", exc)
        return events

    translated = _parse_translation_response(content, len(events))
    if not translated:
        logger.warning("Could not parse translation — using Czech originals")
        return events

    result: list[Event] = []
    for i, ev in enumerate(events):
        tr = translated[i]
        en_title = tr.get("title", ev.title)
        en_desc = tr.get("description", ev.description)

        # Bilingual title: "English / Czech" (skip if identical)
        if en_title.strip() != ev.title.strip() and en_title.strip():
            bi_title = f"{en_title} / {ev.title}"
        else:
            bi_title = ev.title

        # Bilingual description
        dur_str = _format_duration(ev)
        bi_desc = _build_bilingual_description(en_desc, ev.description, ev, dur_str)

        result.append(replace(ev, title=bi_title, description=bi_desc, translated=True))

    return result
