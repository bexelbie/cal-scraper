"""Test the container entrypoint."""

import os
import subprocess
from pathlib import Path


def test_entrypoint_passes_cli_arguments(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    args_file = tmp_path / "args"
    command = bin_dir / "cal-scraper"
    command.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" > {args_file}\n")
    command.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["CAL_SCRAPER_OUTPUT_DIR"] = "/feeds"
    env["CAL_SCRAPER_CACHE_DIR"] = "/cache"

    subprocess.run(
        [
            "sh",
            Path(__file__).parents[1] / "entrypoint.sh",
            "--site",
            "vida",
            "--dry-run",
        ],
        env=env,
        check=True,
    )

    assert args_file.read_text().splitlines() == [
        "--output-dir",
        "/feeds",
        "--cache-dir",
        "/cache",
        "--site",
        "vida",
        "--dry-run",
    ]
