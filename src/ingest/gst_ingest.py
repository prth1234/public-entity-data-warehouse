"""Ingest GST HSN & SAC Master Data from MIT/Apache-2.0 open-source CBIC mirrors + GST State Code reference."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.ingest.http_client import PoliteHttpClient
from src.ingest.raw_landing import write_raw_payload
from src.ingest.robots_checker import check_robots

HSN_CSV_URL = "https://raw.githubusercontent.com/zee4refer/hsn-sac-codes-india/main/hsn.csv"
SAC_CSV_URL = "https://raw.githubusercontent.com/zee4refer/hsn-sac-codes-india/main/sac.csv"
HSN_CHAPTERS_URL = "https://raw.githubusercontent.com/frontlook-admin/HSN-Code-Classifier/Master/HSNChapters.json"


def ingest_gst_masters(base_dir: Path) -> dict[str, Any]:
    """Download public CBIC-derived HSN/SAC master tables into data/raw/gst_masters/."""
    targets = {
        "hsn.csv": HSN_CSV_URL,
        "sac.csv": SAC_CSV_URL,
        "HSNChapters.json": HSN_CHAPTERS_URL,
    }
    downloaded: dict[str, str] = {}

    with PoliteHttpClient(timeout_s=30.0) as client:
        for filename, url in targets.items():
            verdict = check_robots(url, client=client)
            if not verdict.allowed:
                raise RuntimeError(f"Blocked by robots.txt for {url}: {verdict.reason}")

            resp = client.get(url)
            if resp.status_code != 200:
                raise RuntimeError(f"Failed to fetch {url}: HTTP {resp.status_code}")

            path, _ = write_raw_payload(
                base_dir=base_dir,
                source="gst_masters",
                filename=filename,
                payload=resp.content,
                source_url=resp.url,
                http_status=resp.status_code,
                source_version="cbic-open-mirror-2026-11",
            )
            downloaded[filename] = str(path)

    return {"source": "gst_masters", "files": downloaded}


if __name__ == "__main__":
    print(ingest_gst_masters(Path.cwd()))
