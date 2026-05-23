#!/bin/sh
# ABOUTME: Container entrypoint — runs cal-scraper once to produce both Czech and translated feeds.
# ABOUTME: Translation is auto-enabled when Azure OpenAI env vars are present.

set -u

OUTPUT_DIR="${CAL_SCRAPER_OUTPUT_DIR:-/app-data/output}"
CACHE_DIR="${CAL_SCRAPER_CACHE_DIR:-/app-data/cache}"

cal-scraper --output-dir "$OUTPUT_DIR" --cache-dir "$CACHE_DIR"
exit $?
