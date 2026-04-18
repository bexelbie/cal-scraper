#!/bin/sh
# ABOUTME: Container entrypoint — runs cal-scraper once to produce both Czech and translated feeds.
# ABOUTME: Translation is auto-enabled when Azure OpenAI env vars are present.

set -u

OUTPUT_DIR="${CAL_SCRAPER_OUTPUT_DIR:-/data}"

cal-scraper --output-dir "$OUTPUT_DIR"
exit $?
