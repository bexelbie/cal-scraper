"""Generate an index.html listing all .ics calendars in the output directory.

Scans the output directory for every .ics file and reads calendar metadata
directly from each file's headers:
    X-WR-CALNAME     — calendar display name
    X-WR-CALDESC     — calendar description
    X-CAL-SOURCE-URL — original venue URL (custom property set by ics_generator)

For index display, the trailing ``Source: <url>`` clause is stripped from
descriptions to avoid duplication — the URL is rendered as a dedicated link
instead.

When multiple .ics files share the same ``X-CAL-SOURCE-URL`` they are
grouped into a single card (e.g. CZ original + EN translation side-by-side).

Uses string.Template from the stdlib for lightweight templating.
A default template ships alongside this module; users can supply
their own via --index-template.

Public API:
    generate_index(output_dir, ...) — render index.html string
"""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from string import Template

from cal_scraper.models import PRAGUE_TZ

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATE = Path(__file__).parent / "index.html.template"


# ---------------------------------------------------------------------------
# Calendar metadata from .ics files
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CalendarInfo:
    """Metadata for a single .ics file to be listed in the index."""

    filename: str
    cal_name: str
    cal_desc: str
    source_url: str
    updated_at: datetime | None = None


def _read_ics_property(path: Path, prop: str) -> str:
    """Read a top-level ICS property value from a file (cheap line scan).

    Handles RFC 5545 line folding (continuation lines starting with a space
    or tab) and unescapes ``\\,`` → ``,`` / ``\\;`` → ``;`` / ``\\\\`` → ``\\``.
    """
    prefix = f"{prop}:"
    try:
        with path.open(encoding="utf-8") as fh:
            value: str | None = None
            for raw_line in fh:
                line = raw_line.rstrip("\r\n")
                # Continuation line: starts with a single space or tab
                if value is not None and line[:1] in (" ", "\t"):
                    value += line[1:]
                    continue
                # If we were accumulating, we're done — return it
                if value is not None:
                    return _ics_unescape(value)
                if line.upper().startswith(prefix.upper()):
                    value = line[len(prefix):]
                    continue
                if line.strip().upper() == "BEGIN:VEVENT":
                    break
            # Property was the last line before EOF (or before VEVENT)
            if value is not None:
                return _ics_unescape(value)
    except OSError:
        pass
    return ""


def _ics_unescape(value: str) -> str:
    """Unescape ICS text values (RFC 5545 §3.3.11)."""
    return (
        value.replace("\\n", "\n")
        .replace("\\N", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )


def discover_calendars(output_dir: Path) -> list[CalendarInfo]:
    """Scan output_dir for .ics files and read metadata from each."""
    ics_files = sorted(output_dir.glob("*.ics"))
    results: list[CalendarInfo] = []
    for ics_path in ics_files:
        cal_name = _read_ics_property(ics_path, "X-WR-CALNAME") or ics_path.name
        cal_desc = _read_ics_property(ics_path, "X-WR-CALDESC")
        source_url = _read_ics_property(ics_path, "X-CAL-SOURCE-URL")
        try:
            mtime = ics_path.stat().st_mtime
            updated_at = datetime.fromtimestamp(mtime, tz=PRAGUE_TZ)
        except OSError:
            updated_at = None
        results.append(CalendarInfo(
            filename=ics_path.name,
            cal_name=cal_name,
            cal_desc=cal_desc,
            source_url=source_url,
            updated_at=updated_at,
        ))
    return results


# ---------------------------------------------------------------------------
# Grouping — pair originals with their translations
# ---------------------------------------------------------------------------


def _is_translation(cal: CalendarInfo) -> bool:
    """Return True if *cal* is an auto-translated variant."""
    return (
        "auto-translated" in cal.cal_name.lower()
        or "auto-translated" in cal.cal_desc.lower()
    )


def _group_calendars(calendars: list[CalendarInfo]) -> list[list[CalendarInfo]]:
    """Group calendars that share the same ``source_url``.

    Within each group the original-language calendar comes first,
    followed by translations.  Calendars with no ``source_url`` or a
    unique ``source_url`` form their own single-item group.

    Insertion order is preserved — the first file encountered for a given
    ``source_url`` determines the group's position.
    """
    groups: list[list[CalendarInfo]] = []
    url_to_idx: dict[str, int] = {}

    for cal in calendars:
        if cal.source_url and cal.source_url in url_to_idx:
            groups[url_to_idx[cal.source_url]].append(cal)
        elif cal.source_url:
            url_to_idx[cal.source_url] = len(groups)
            groups.append([cal])
        else:
            groups.append([cal])

    # Within each group: originals first, then translations, stable by filename
    for group in groups:
        group.sort(key=lambda c: (1 if _is_translation(c) else 0, c.filename))

    return groups


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------


_SOURCE_TAIL_RE = re.compile(r"\s*Source:\s*https?://\S+\s*$")


def _strip_source_from_desc(desc: str, source_url: str) -> str:
    """Remove the trailing 'Source: <url>' clause for index display."""
    if source_url and desc:
        return _SOURCE_TAIL_RE.sub("", desc).rstrip()
    return desc


def _human_datetime(dt: datetime) -> str:
    """Format *dt* as '20 Apr 2026, 10:00 am'."""
    day = dt.day
    month_year = dt.strftime("%b %Y")
    hour = dt.hour % 12 or 12
    minute = dt.strftime("%M")
    ampm = "am" if dt.hour < 12 else "pm"
    return f"{day} {month_year}, {hour}:{minute} {ampm}"


def _format_updated(updated: datetime) -> str:
    """Return an HTML ``<time>`` snippet with a human-readable timestamp."""
    iso = html.escape(updated.isoformat())
    fmt = html.escape(_human_datetime(updated))
    return f'<time datetime="{iso}">{fmt}</time>'


def _ics_href(cal: CalendarInfo, base_url: str) -> str:
    """Build the subscribe href for a calendar file."""
    if base_url:
        # Strip any scheme the user may have pasted in, and trailing slashes
        clean = base_url.split("://", 1)[-1].rstrip("/")
        return html.escape(f"webcal://{clean}/{cal.filename}")
    return html.escape(cal.filename)


_LANG_SUFFIX_RE = re.compile(r"\s*\((?:in )?CZ\)\s*$", re.IGNORECASE)


def _clean_group_title(name: str, is_group: bool) -> str:
    """Strip the language suffix like '(in CZ)' when the card already has CZ/EN buttons."""
    if is_group:
        return _LANG_SUFFIX_RE.sub("", name).rstrip(" –—-")
    return name


def _render_calendar_group(group: list[CalendarInfo], base_url: str = "") -> str:
    """Render the HTML snippet for a group of related calendars.

    A group may contain a single calendar or an original + translated pair.
    The primary (original-language) calendar supplies the card title,
    description, and source link.  Each calendar in the group gets its own
    subscribe button, labelled with a language tag when the group has more
    than one member.
    """
    primary = group[0]
    is_group = len(group) > 1

    name = html.escape(_clean_group_title(primary.cal_name, is_group))
    clean_desc = _strip_source_from_desc(primary.cal_desc, primary.source_url)
    desc = html.escape(clean_desc) if clean_desc else ""
    source = html.escape(primary.source_url) if primary.source_url else ""

    # Use the most recent mtime across all files in the group
    all_updated = [c.updated_at for c in group if c.updated_at is not None]
    latest_updated = max(all_updated) if all_updated else None

    # Meta line: description + updated timestamp
    meta_parts: list[str] = []
    if desc:
        meta_parts.append(desc)
    if latest_updated:
        meta_parts.append(f"Updated {_format_updated(latest_updated)}")

    lines = ['<div class="calendar">']
    lines.append(f"  <h2>{name}</h2>")

    if meta_parts:
        lines.append(f'  <p class="meta">{" · ".join(meta_parts)}</p>')

    # Action buttons
    lines.append('  <p class="actions">')
    if len(group) == 1:
        href = _ics_href(group[0], base_url)
        lines.append(f'    <a class="subscribe" href="{href}">📅 Subscribe</a>')
    else:
        for cal in group:
            href = _ics_href(cal, base_url)
            lang = "EN" if _is_translation(cal) else "CZ"
            lines.append(f'    <a class="subscribe" href="{href}">📅 {lang}</a>')
    if source:
        lines.append(f'    <a class="source" href="{source}">🔗 Source</a>')
    lines.append("  </p>")
    lines.append("</div>")
    return "\n".join(lines)


def generate_index(
    output_dir: Path,
    *,
    template_path: Path | None = None,
    title: str = "Calendar Feeds",
    subtitle: str = "iCal feeds scraped by cal-scraper",
    base_url: str = "",
) -> str:
    """Render the index HTML page listing all .ics files in output_dir.

    Parameters
    ----------
    output_dir
        Directory to scan for .ics files.
    template_path
        Path to a custom template file. Uses the built-in default when None.
    title
        Page title inserted as ``$title``.
    subtitle
        Page subtitle inserted as ``$subtitle``.
    base_url
        When set (e.g. ``cal.example.com``), subscribe links become
        ``webcal://<base_url>/<filename>`` for one-click subscription.

    Returns
    -------
    str
        The rendered HTML page.
    """
    tpl_path = template_path or DEFAULT_TEMPLATE
    tpl_text = tpl_path.read_text(encoding="utf-8")
    tpl = Template(tpl_text)

    calendars = discover_calendars(output_dir)
    groups = _group_calendars(calendars)
    blocks = [_render_calendar_group(group, base_url=base_url) for group in groups]
    calendars_html = "\n\n".join(blocks)

    now_dt = datetime.now(tz=PRAGUE_TZ)
    now = _human_datetime(now_dt)
    tz_name = now_dt.strftime("%Z")

    return tpl.safe_substitute(
        title=title,
        subtitle=subtitle,
        calendars=calendars_html,
        generated_at=now,
        timezone_note=f"All times shown in {tz_name}.",
    )
