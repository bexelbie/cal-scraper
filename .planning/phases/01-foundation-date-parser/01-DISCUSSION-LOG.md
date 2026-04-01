# Phase 1: Foundation & Date Parser - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 01-foundation-date-parser
**Areas discussed:** Default duration, Multi-day events, Unknown formats, Package layout

---

## Default Duration

| Option | Description | Selected |
|--------|-------------|----------|
| 1 hour | Short default for gallery events | |
| 2 hours | Standard museum event length | ✓ |
| 3 hours | Longer default | |

**User's choice:** 2 hours
**Notes:** Direct answer without discussion needed.

---

## Multi-Day Events

| Option | Description | Selected |
|--------|-------------|----------|
| Single spanning event | One VEVENT covering the full date range (all-day) | ✓ |
| Daily entries | Separate VEVENT for each day in the range | |

**User's choice:** Spanning event, all day
**Notes:** Clear preference for simplicity.

---

## Unknown Formats

| Option | Description | Selected |
|--------|-------------|----------|
| Fail hard | Raise exception on unparseable dates | |
| Warn and skip | Log warning, skip event, continue processing | ✓ |
| Best-effort guess | Try to extract partial info | |

**User's choice:** Warn and skip
**Notes:** Resilient processing preferred.

---

## Package Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Single script | One .py file | |
| Minimal package | Simple module structure | |
| Agent's discretion | Keep it simple, YAGNI | ✓ |

**User's choice:** Agent's discretion — YAGNI applies, not a generalized parser
**Notes:** User emphasized this is a focused single-site tool, not a framework.

---

## Agent's Discretion

- Package layout (single script vs package)
- Data model design
- Test framework choice

## Deferred Ideas

None
