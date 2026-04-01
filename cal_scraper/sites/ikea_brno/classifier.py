"""Keyword-based kids event classification for IKEA events."""

from __future__ import annotations

KIDS_KW = [
    "děti", "dětí", "dětský", "dětem", "milé děti",
    "malování", "stříhání", "lepení",
    "småland", "škudlík", "pohád",
]

PROMO_KW = [
    "kč", "kupón", "kupte", "slev", "úvěr",
    "splátk", "zaplate", "nákup", "zdarma",
    "nabídka", "zvýhodn",
]


def _extract_text(event: dict) -> str:
    """Extract searchable text from event details (Czech locale)."""
    details = event.get("eventDetails", {}).get("cs", {})
    parts = [
        details.get("eventName", "") or "",
        details.get("eventIntroduction", "") or "",
        details.get("eventDescription", "") or "",
    ]
    return " ".join(parts).lower()


def _event_duration_days(event: dict) -> int:
    """Calculate the total event duration in days across all timeslots."""
    max_days = 0
    for slot in event.get("timeSlots", []):
        utc_start = slot.get("utcStartDate", 0)
        utc_end = slot.get("utcEndDate", 0)
        if utc_start and utc_end:
            days = (utc_end - utc_start) / 86400
            if days > max_days:
                max_days = days
    return int(max_days)


def classify_event(event: dict) -> str:
    """Classify an event into one of: kids, kids-promo, kids-ongoing, adult, promo.

    Rules:
    1. Duration >7 days + no KIDS_KW → "promo"
    2. Duration >7 days + KIDS_KW + PROMO_KW → "kids-promo"
    3. Duration >7 days + KIDS_KW → "kids-ongoing"
    4. KIDS_KW + no PROMO_KW + ≤7 days → "kids"
    5. Everything else → "adult"
    """
    text = _extract_text(event)
    duration = _event_duration_days(event)

    has_kids = any(kw in text for kw in KIDS_KW)
    has_promo = any(kw in text for kw in PROMO_KW)

    if duration > 7:
        if not has_kids:
            return "promo"
        if has_promo:
            return "kids-promo"
        return "kids-ongoing"

    if has_kids and not has_promo:
        return "kids"

    return "adult"


def is_kids_event(event: dict) -> bool:
    """Return True if the event is classified as any kids category."""
    return classify_event(event).startswith("kids")


def filter_kids_events(events: list[dict]) -> list[dict]:
    """Return only events classified as kids events."""
    return [e for e in events if is_kids_event(e)]
