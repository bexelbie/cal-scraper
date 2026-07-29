"""Emit a fleet fact line-protocol record for cal-scraper runs."""

from __future__ import annotations

import base64
import json
import os
import sys
import time
from pathlib import Path


def _escape_tag_value(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(" ", "\\ ")
        .replace(",", "\\,")
        .replace("=", "\\=")
    )


def _escape_string_field(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def emit_fleet_fact(
    detail: dict[str, object],
    status: str,
    *,
    ts: int | None = None,
    output_dir: str | None = None,
    host: str | None = None,
    service: str = "cal-scraper",
    fact: str = "run",
) -> tuple[Path | None, str | None]:
    """Write a fleet fact file in InfluxDB line-protocol format."""
    fact_dir = (output_dir or os.environ.get("FLEET_FACT_DIR", "")).strip()
    if not fact_dir:
        print("Skipping fleet fact emission: FLEET_FACT_DIR not set", file=sys.stderr)
        return None, None

    resolved_host = host or os.environ.get("FLEET_HOST") or os.uname().nodename
    resolved_ts = int(ts if ts is not None else time.time())
    detail_json = json.dumps(detail, sort_keys=True, separators=(",", ":"))
    detail_b64 = base64.b64encode(detail_json.encode()).decode()

    tag_string = ",".join(
        [
            f"host={_escape_tag_value(resolved_host)}",
            f"service={_escape_tag_value(service)}",
            f"fact={_escape_tag_value(fact)}",
        ]
    )
    field_string = ",".join(
        [
            "schema=1i",
            f'status="{_escape_string_field(status)}"',
            f"ts={resolved_ts}i",
            f'detail_b64_json="{_escape_string_field(detail_b64)}"',
        ]
    )
    line = f"fleet_fact,{tag_string} {field_string}"

    out_dir = Path(fact_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Stable name, overwritten each run (matches the heartbeat pattern): Telegraf's
    # inputs.file re-reads the whole dir every interval, so one file per (service,fact)
    # keeps the retained topic at the latest value instead of accumulating stale files.
    # Write-then-replace so the poller never sees a half-written file.
    out_path = out_dir / f"{service}-{fact}"
    tmp_path = out_dir / f"{service}-{fact}.tmp"
    tmp_path.write_text(line + "\n", encoding="utf-8")
    os.replace(tmp_path, out_path)
    return out_path, line
