"""Translate events from Czech to English using Azure OpenAI.

Produces bilingual Event objects with:
- Title: "English / Czech"
- Description: English text → details → Czech text

Translates events individually (one API call per event) and caches results
in a SQLite database so unchanged events are never re-translated.

Public API:
    load_azure_config()           — load config from env vars
    translate_events(events, cfg, site, cache) — returns bilingual Events
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import replace

import requests as http_requests

from cal_scraper.models import Event
from cal_scraper.translation_cache import TranslationCache

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
# Single-event translation
# ---------------------------------------------------------------------------


def _parse_single_response(raw: str) -> dict | None:
    """Parse a single {title, description} JSON object from LLM output.

    Returns the parsed dict or None on failure.
    """
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3].rstrip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Translation response is not valid JSON")
        return None

    if not isinstance(parsed, dict):
        logger.warning("Translation response is not a JSON object")
        return None

    if "title" not in parsed or "description" not in parsed:
        logger.warning("Translation response missing 'title' or 'description' keys")
        return None

    return parsed


def translate_single_event(
    event: Event,
    config: dict[str, str],
) -> tuple[str, str] | None:
    """Translate one event via a single LLM call.

    Returns (title_en, description_en) or None on failure.
    """
    item = json.dumps(
        {"title": event.title, "description": event.description},
        ensure_ascii=False,
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Translate the title and description from Czech to English. "
                'Return a JSON object: {"title": "...", "description": "..."}\n\n'
                + item
            ),
        },
    ]

    try:
        resp = _call_azure_openai(config, messages)
        content = resp["choices"][0]["message"]["content"]
    except (TranslationError, KeyError, IndexError) as exc:
        logger.warning("Translation failed for '%s': %s", event.title, exc)
        return None

    try:
        finish_reason = resp["choices"][0].get("finish_reason", "")
        if finish_reason == "length":
            logger.warning(
                "Translation truncated (finish_reason=length) for '%s'",
                event.title,
            )
            return None
    except (KeyError, IndexError):
        pass

    parsed = _parse_single_response(content)
    if parsed is None:
        return None

    return parsed["title"], parsed["description"]


# ---------------------------------------------------------------------------
# Bilingual event assembly
# ---------------------------------------------------------------------------


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

    parts.append(
        "⚠️ Unofficial source – verify details on the organizer's website. "
        "Auto-translated via Azure OpenAI."
    )

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

    parts.append("⚠️ Neoficiální zdroj – ověřte si detaily na webu pořadatele.")

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


# ---------------------------------------------------------------------------
# Main translation entry point
# ---------------------------------------------------------------------------


def translate_events(
    events: list[Event],
    config: dict[str, str],
    *,
    site: str = "",
    cache: TranslationCache | None = None,
) -> tuple[list[Event], bool]:
    """Translate a list of events to bilingual English/Czech.

    Each event is translated individually. If a cache is provided, cached
    translations are reused and only new/changed events hit the API.

    Returns a tuple of (bilingual_events, all_succeeded):
    - bilingual_events: Event objects with translated content where available,
      Czech fallback where translation failed
    - all_succeeded: True if every event was translated (from cache or API)
    """
    if not events:
        return events, True

    result_events: list[Event] = []
    failures = 0
    cache_hits = 0
    api_calls = 0

    for ev in events:
        en_title: str | None = None
        en_desc: str | None = None

        # Check cache first
        if cache is not None:
            cached = cache.get(site, ev)
            if cached is not None:
                en_title, en_desc = cached
                cache_hits += 1

        # Cache miss — call API
        if en_title is None:
            result = translate_single_event(ev, config)
            api_calls += 1
            if result is not None:
                en_title, en_desc = result
                # Store in cache for next run
                if cache is not None:
                    cache.put(site, ev, en_title, en_desc)
            else:
                # Retry once
                result = translate_single_event(ev, config)
                api_calls += 1
                if result is not None:
                    en_title, en_desc = result
                    if cache is not None:
                        cache.put(site, ev, en_title, en_desc)

        # Build bilingual event or fall back to Czech
        if en_title is not None and en_desc is not None:
            if en_title.strip() != ev.title.strip() and en_title.strip():
                bi_title = f"{en_title} / {ev.title}"
            else:
                bi_title = ev.title

            dur_str = _format_duration(ev)
            bi_desc = _build_bilingual_description(en_desc, ev.description, ev, dur_str)
            result_events.append(
                replace(ev, title=bi_title, description=bi_desc, translated=True)
            )
        else:
            # Translation failed — use Czech original with bilingual framing
            failures += 1
            logger.warning("Using Czech fallback for '%s'", ev.title)
            result_events.append(ev)

    logger.info(
        "Translation: %d cache hits, %d API calls, %d failures",
        cache_hits,
        api_calls,
        failures,
    )
    return result_events, failures == 0
