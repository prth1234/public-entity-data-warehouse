"""Ingest All India Pincode Directory from MIT-licensed data.gov.in mirror."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.ingest.http_client import PoliteHttpClient
from src.ingest.raw_landing import write_raw_payload
from src.ingest.robots_checker import check_robots

PINCODE_CSV_URL = "https://raw.githubusercontent.com/dropdevrahul/pincodes-india/main/pincode.csv"


def ingest_pincode_directory(base_dir: Path) -> dict[str, Any]:
    """Download All India Pincode Directory CSV into data/raw/india_post_pincode/."""
    with PoliteHttpClient(timeout_s=60.0) as client:
        verdict = check_robots(PINCODE_CSV_URL, client=client)
        if not verdict.allowed:
            raise RuntimeError(f"Blocked by robots.txt: {verdict.reason}")

        resp = client.get(PINCODE_CSV_URL)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to download pincode.csv: HTTP {resp.status_code}")

        path, _ = write_raw_payload(
            base_dir=base_dir,
            source="india_post_pincode",
            filename="pincode.csv",
            payload=resp.content,
            source_url=resp.url,
            http_status=resp.status_code,
            source_version="2026-10-29-mit-mirror",
        )
        return {
            "source": "india_post_pincode",
            "robots_allowed": verdict.allowed,
            "byte_size": len(resp.content),
            "file": str(path),
        }


if __name__ == "__main__":
    print(ingest_pincode_directory(Path.cwd()))
