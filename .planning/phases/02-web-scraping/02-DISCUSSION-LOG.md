# Phase 2: Web Scraping - Discussion Log

**Phase:** 02-web-scraping
**Date:** 2026-04-01
**Mode:** Interactive (discuss)
**Duration:** 1 round

## Questions & Answers

### Q1: Pagination strategy
**Options presented:**
1. Parse data-settings JSON from div.ecs-posts for max_num_pages
2. Follow next-page links
3. Agent's discretion

**User response:** "do the right thing - do you need my help here for real?"
**Decision:** D-01 — Agent's discretion on pagination approach. Dynamic discovery required.

### Q2: Extraction completeness (missing fields)
**Options presented:**
1. Skip events with missing fields
2. Partial extract with warnings
3. Warn and skip

**User response:** "warn on events we can't parse"
**Decision:** D-02 — Warn and skip incomplete events.

### Q3: Request resilience (retries, failure handling)
**Options presented:**
1. Retry N times with backoff
2. Warn on fails, produce output
3. Bail on high failure rate

**User response:** "This is a one-shot script. Warn on fails, produce output. If we're getting a lot of fails, we should probably bail on the run. The idea is this runs once a day and it updates a fucking calendar. We aren't going to the moon here."
**Decision:** D-03 — Warn on individual failures, bail on mass failures. Keep it simple. D-04 — Polite scraping (1s delay, User-Agent).

## Summary

User emphasized simplicity and pragmatism. This is a daily cron-style script, not a mission-critical system. Error handling should be proportional: warn and continue for individual issues, bail out if something is fundamentally broken.

---

*Phase: 02-web-scraping*
*Discussion completed: 2026-04-01*
