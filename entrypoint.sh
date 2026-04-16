#!/bin/sh
# ABOUTME: Container entrypoint — runs cal-scraper twice: Czech feeds then translated feeds.
# ABOUTME: Aggregates exit codes: any failure = exit 1 (strict mode for systemd alerting).

set -u

OUTPUT_DIR="${CAL_SCRAPER_OUTPUT_DIR:-/data}"
rc=0

# --- Czech feeds (always) ---
echo "=== Czech feeds ===" >&2
cal-scraper --output-dir "$OUTPUT_DIR"
czech_rc=$?
if [ "$czech_rc" -ne 0 ]; then
    echo "Czech feed run had failures (exit $czech_rc)" >&2
    rc=1
fi

# --- Translated feeds (only if Azure config is present) ---
if [ -n "${AZURE_OPENAI_ENDPOINT:-}" ] && [ -n "${AZURE_OPENAI_KEY:-}" ]; then
    echo "=== Translated feeds ===" >&2
    cal-scraper --translate --output-dir "$OUTPUT_DIR" --filename-suffix=-en
    translate_rc=$?
    if [ "$translate_rc" -ne 0 ]; then
        echo "Translated feed run had failures (exit $translate_rc)" >&2
        rc=1
    fi
else
    echo "Skipping translation: AZURE_OPENAI_ENDPOINT/KEY not set" >&2
fi

exit $rc
