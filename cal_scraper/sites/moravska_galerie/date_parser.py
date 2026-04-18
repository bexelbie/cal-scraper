"""Czech date/time parser for Moravská galerie event listings.

Parses all observed date format variants from the gallery site into
typed ParsedDate objects with timezone-aware datetimes in Europe/Prague.

Format variants handled (DATE-01 through DATE-07):
  - "31/3/2026, 15 H"              → single day + whole hour
  - "8/4/2026, 16.30 H"            → single day + hour.minutes
  - "23/5/2026, 13–22 H"           → single day + time range
  - "23/5/2026"                     → date only (all-day event)
  - "7/7 – 11/7/2026"              → multi-day range (en-dash)
  - "27/7 – 31/7/2026, 9–16 H"    → multi-day + time range
  - "24/5/2026, 15 H / 16 H / 17 H" → multiple time slots (first used)

Unrecognized formats fall back to Azure OpenAI when credentials are
available.  The LLM is asked to return structured JSON which is then
validated and converted to ParsedDate objects.
"""

import json
import logging
import re
from datetime import date, datetime, timedelta

from cal_scraper.models import DEFAULT_DURATION, PRAGUE_TZ, ParsedDate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def _clean(raw: str) -> str:
    """Strip ● bullet prefix and normalize whitespace."""
    text = raw.strip()
    text = re.sub(r"^●\s*", "", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dt(day: int, month: int, year: int, hour: int, minute: int = 0) -> datetime:
    """Create timezone-aware datetime in Europe/Prague."""
    return datetime(year, month, day, hour, minute, tzinfo=PRAGUE_TZ)


def _make_date(day: int, month: int, year: int) -> date:
    """Create a date object (D/M/Y European order)."""
    return date(year, month, day)


# ---------------------------------------------------------------------------
# Regex patterns — ORDERED most specific → least specific (CRITICAL)
# ---------------------------------------------------------------------------

# Pattern a: Multi-day + time range  "27/7 – 31/7/2026, 9–16 H"
_RE_MULTI_DAY_TIME = re.compile(
    r"(\d{1,2})/(\d{1,2})\s*\u2013\s*(\d{1,2})/(\d{1,2})/(\d{4}),\s*(\d{1,2})\u2013(\d{1,2})\s*H"
)

# Pattern b: Multi-day no time  "7/7 – 11/7/2026"
_RE_MULTI_DAY = re.compile(
    r"(\d{1,2})/(\d{1,2})\s*\u2013\s*(\d{1,2})/(\d{1,2})/(\d{4})$"
)

# Pattern c: Single day + hour.minutes  "8/4/2026, 16.30 H"
_RE_SINGLE_HM = re.compile(
    r"(\d{1,2})/(\d{1,2})/(\d{4}),\s*(\d{1,2})\.(\d{2})\s*H"
)

# Pattern c2: Single day + time range  "23/5/2026, 13–22 H"
_RE_SINGLE_RANGE = re.compile(
    r"(\d{1,2})/(\d{1,2})/(\d{4}),\s*(\d{1,2})\u2013(\d{1,2})\s*H$"
)

# Pattern d: Multiple time slots  "24/5/2026, 15 H / 16 H / 17 H"
_RE_MULTI_TIME = re.compile(
    r"(\d{1,2})/(\d{1,2})/(\d{4}),\s*(\d{1,2})\s*H\s*/"
)
_RE_MULTI_TIME_HOURS = re.compile(r"(\d{1,2})\s*H")

# Pattern e: Single day + whole hour  "31/3/2026, 15 H"
_RE_SINGLE_H = re.compile(
    r"(\d{1,2})/(\d{1,2})/(\d{4}),\s*(\d{1,2})\s*H$"
)

# Pattern f: Date only  "23/5/2026"
_RE_DATE_ONLY = re.compile(
    r"^(\d{1,2})/(\d{1,2})/(\d{4})$"
)


# ---------------------------------------------------------------------------
# Handler functions (one per pattern)
# ---------------------------------------------------------------------------

def _parse_multi_day_time(m: re.Match, raw: str) -> ParsedDate:
    """'27/7 – 31/7/2026, 9–16 H' → all-day spanning event.

    Multi-day camps with daily hours render better as all-day banners
    in calendar apps than as a single massive timed block.
    """
    sd, sm = int(m.group(1)), int(m.group(2))
    ed, em, year = int(m.group(3)), int(m.group(4)), int(m.group(5))
    start = _make_date(sd, sm, year)
    end = _make_date(ed, em, year) + timedelta(days=1)  # exclusive DTEND
    return ParsedDate(dtstart=start, dtend=end, all_day=True, raw_text=raw)


def _parse_multi_day(m: re.Match, raw: str) -> ParsedDate:
    """'7/7 – 11/7/2026' → all-day spanning event (D-02)."""
    sd, sm = int(m.group(1)), int(m.group(2))
    ed, em, year = int(m.group(3)), int(m.group(4)), int(m.group(5))
    start = _make_date(sd, sm, year)
    end = _make_date(ed, em, year) + timedelta(days=1)  # exclusive DTEND
    return ParsedDate(dtstart=start, dtend=end, all_day=True, raw_text=raw)


def _parse_single_hm(m: re.Match, raw: str) -> ParsedDate:
    """'8/4/2026, 16.30 H' → timed event with dot-separated minutes."""
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    h, mi = int(m.group(4)), int(m.group(5))
    start = _make_dt(d, mo, y, h, mi)
    end = start + DEFAULT_DURATION
    return ParsedDate(dtstart=start, dtend=end, all_day=False, raw_text=raw, estimated_end=True)


def _parse_single_range(m: re.Match, raw: str) -> ParsedDate:
    """'23/5/2026, 13–22 H' → timed event with explicit start and end hours."""
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    h_start, h_end = int(m.group(4)), int(m.group(5))
    start = _make_dt(d, mo, y, h_start)
    end = _make_dt(d, mo, y, h_end)
    return ParsedDate(dtstart=start, dtend=end, all_day=False, raw_text=raw)


def _parse_multi_time(m: re.Match, raw: str) -> list[ParsedDate]:
    """'24/5/2026, 15 H / 16 H / 17 H' → one ParsedDate per time slot."""
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    hours = [int(h) for h in _RE_MULTI_TIME_HOURS.findall(raw)]
    results = []
    for h in hours:
        start = _make_dt(d, mo, y, h)
        end = start + DEFAULT_DURATION
        results.append(ParsedDate(dtstart=start, dtend=end, all_day=False, raw_text=raw, estimated_end=True))
    return results


def _parse_single_h(m: re.Match, raw: str) -> ParsedDate:
    """'31/3/2026, 15 H' → timed event with 2h default duration (D-01)."""
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    h = int(m.group(4))
    start = _make_dt(d, mo, y, h)
    end = start + DEFAULT_DURATION
    return ParsedDate(dtstart=start, dtend=end, all_day=False, raw_text=raw, estimated_end=True)


def _parse_date_only(m: re.Match, raw: str) -> ParsedDate:
    """'23/5/2026' → all-day event with exclusive end."""
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    start = _make_date(d, mo, y)
    end = start + timedelta(days=1)
    return ParsedDate(dtstart=start, dtend=end, all_day=True, raw_text=raw)


# ---------------------------------------------------------------------------
# Pattern → handler dispatch table (order is CRITICAL)
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[re.Pattern, callable]] = [
    (_RE_MULTI_DAY_TIME, _parse_multi_day_time),
    (_RE_MULTI_DAY,      _parse_multi_day),
    (_RE_SINGLE_HM,      _parse_single_hm),
    (_RE_SINGLE_RANGE,   _parse_single_range),
    (_RE_MULTI_TIME,     _parse_multi_time),
    (_RE_SINGLE_H,       _parse_single_h),
    (_RE_DATE_ONLY,      _parse_date_only),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_date(raw_text: str) -> ParsedDate | None:
    """Parse a Czech date string into a ParsedDate, or None if unrecognized.

    For multi-time-slot formats, returns only the first slot.
    Use parse_dates() to get all time slots.
    """
    results = parse_dates(raw_text)
    return results[0] if results else None


def parse_dates(raw_text: str) -> list[ParsedDate]:
    """Parse a Czech date string into a list of ParsedDate objects.

    Returns multiple results for multi-time-slot formats (e.g. "15 H / 16 H / 17 H").
    Returns a single-element list for all other recognized formats.
    Falls back to LLM parsing when regex fails and Azure OpenAI is configured.
    Returns an empty list for unrecognized formats (with a logged warning).
    """
    cleaned = _clean(raw_text)
    if not cleaned:
        logger.warning("Unrecognized date format: %r", raw_text)
        return []

    for pattern, handler in _PATTERNS:
        match = pattern.search(cleaned)
        if match:
            result = handler(match, cleaned)
            if isinstance(result, list):
                return result
            return [result]

    # Regex exhausted — try LLM fallback
    llm_result = _llm_parse_date(cleaned)
    if llm_result:
        logger.info("LLM fallback parsed date: %r", raw_text)
        return llm_result

    logger.warning("Unrecognized date format: %r", raw_text)
    return []


# ---------------------------------------------------------------------------
# LLM fallback for unrecognized date formats
# ---------------------------------------------------------------------------

_LLM_SYSTEM_PROMPT = """\
You parse Czech date/time strings from event listings into structured JSON.
Dates use European D/M/YYYY order.  Times use 24-hour format.
"H" means hours (e.g. "15 H" = 15:00).  "–" (en-dash) separates ranges.

Return a JSON array of objects.  Each object represents one time slot:
{
  "start_day": int, "start_month": int, "start_year": int,
  "start_hour": int or null, "start_minute": int or null,
  "end_day": int or null, "end_month": int or null, "end_year": int or null,
  "end_hour": int or null, "end_minute": int or null,
  "all_day": bool
}

Rules:
- If only a start time is given (no end time), set end_hour/end_minute to null.
- If the string has no time at all, set all_day=true, all hour/minute fields null.
- For multi-day ranges without times, set all_day=true.
- For multi-day ranges with daily hours, set all_day=true (calendar apps show them as banners).
- Return ONLY the JSON array, no markdown fences, no explanation.
"""


def _llm_parse_date(cleaned: str) -> list[ParsedDate]:
    """Attempt to parse a date string using Azure OpenAI.

    Returns a list of ParsedDate objects on success, or an empty list if
    LLM is unavailable or returns unparseable output.
    """
    try:
        from cal_scraper.translator import TranslationError, load_azure_config, _call_azure_openai
    except ImportError:
        return []

    try:
        config = load_azure_config()
    except (TranslationError, Exception):
        return []

    messages = [
        {"role": "system", "content": _LLM_SYSTEM_PROMPT},
        {"role": "user", "content": cleaned},
    ]

    try:
        resp = _call_azure_openai(config, messages, max_tokens=300)
        content = resp["choices"][0]["message"]["content"].strip()
        # Strip markdown fences if the model wraps them anyway
        if content.startswith("```"):
            content = re.sub(r"^```\w*\n?", "", content)
            content = re.sub(r"\n?```$", "", content)
        slots = json.loads(content)
    except (TranslationError, KeyError, json.JSONDecodeError, Exception) as exc:
        logger.warning("LLM date parse failed for %r: %s", cleaned, exc)
        return []

    if not isinstance(slots, list):
        slots = [slots]

    results: list[ParsedDate] = []
    for slot in slots:
        try:
            parsed = _slot_to_parsed_date(slot, cleaned)
            if parsed:
                results.append(parsed)
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("LLM returned invalid date slot for %r: %s", cleaned, exc)

    return results


def _slot_to_parsed_date(slot: dict, raw: str) -> ParsedDate | None:
    """Convert a single LLM JSON slot to a ParsedDate, or None on bad data."""
    sd = int(slot["start_day"])
    sm = int(slot["start_month"])
    sy = int(slot["start_year"])
    all_day = bool(slot.get("all_day", False))

    if all_day:
        start = _make_date(sd, sm, sy)
        ed = slot.get("end_day")
        if ed is not None and slot.get("end_month") is not None:
            ey = int(slot.get("end_year", sy))
            end = _make_date(int(ed), int(slot["end_month"]), ey) + timedelta(days=1)
        else:
            end = start + timedelta(days=1)
        return ParsedDate(dtstart=start, dtend=end, all_day=True, raw_text=raw)

    sh = slot.get("start_hour")
    smi = slot.get("start_minute") or 0
    if sh is None:
        # No time info but not marked all-day — treat as all-day
        start = _make_date(sd, sm, sy)
        end = start + timedelta(days=1)
        return ParsedDate(dtstart=start, dtend=end, all_day=True, raw_text=raw)

    start = _make_dt(sd, sm, sy, int(sh), int(smi))

    eh = slot.get("end_hour")
    if eh is not None:
        emi = slot.get("end_minute") or 0
        ed = slot.get("end_day") or sd
        em = slot.get("end_month") or sm
        ey = slot.get("end_year") or sy
        end = _make_dt(int(ed), int(em), int(ey), int(eh), int(emi))
        return ParsedDate(dtstart=start, dtend=end, all_day=False, raw_text=raw)

    end = start + DEFAULT_DURATION
    return ParsedDate(dtstart=start, dtend=end, all_day=False, raw_text=raw, estimated_end=True)
