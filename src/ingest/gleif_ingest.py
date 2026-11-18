"""Ingest Indian Legal Entity Identifier (LEI) records from official GLEIF API (CC0 public domain)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.ingest.http_client import PoliteHttpClient
from src.ingest.raw_landing import write_raw_payload
from src.ingest.robots_checker import check_robots

GLEIF_API_URL = "https://api.gleif.org/api/v1/lei-records"


def ingest_gleif_india(
    base_dir: Path,
    page_size: int = 100,
    max_records: int = 200,
) -> dict[str, Any]:
    """Fetch Indian LEI records from api.gleif.org into data/raw/gleif_lei/."""
    downloaded_files: list[str] = []
    total_available: int | None = None
    fetched_records = 0

    with PoliteHttpClient(timeout_s=30.0, min_delay_per_host_s=0.5) as client:
        verdict = check_robots(GLEIF_API_URL, client=client)
        if not verdict.allowed:
            raise RuntimeError(f"Blocked by robots.txt: {verdict.reason}")

        page_num = 1
        while fetched_records < max_records:
            params = {
                "filter[entity.legalAddress.country]": "IN",
                "page[size]": min(page_size, max_records - fetched_records),
                "page[number]": page_num,
            }
            resp = client.get(GLEIF_API_URL, params=params)
            if resp.status_code != 200:
                raise RuntimeError(f"GLEIF API returned HTTP {resp.status_code}: {resp.text[:300]}")

            data = json.loads(resp.text)
            if total_available is None:
                total_available = int(data.get("meta", {}).get("pagination", {}).get("total", 0))

            records = data.get("data", [])
            if not records:
                break

            filename = f"gleif_in_page_{page_num:04d}.json"
            path, _ = write_raw_payload(
                base_dir=base_dir,
                source="gleif_lei",
                filename=filename,
                payload=resp.content,
                source_url=resp.url,
                http_status=resp.status_code,
                source_version="gleif-v1",
            )
            downloaded_files.append(str(path))
            fetched_records += len(records)
            page_num += 1

    return {
        "source": "gleif_lei",
        "total_available_in_api": total_available,
        "fetched_records": fetched_records,
        "pages": len(downloaded_files),
        "robots_allowed": verdict.allowed,
        "files": downloaded_files,
    }


if __name__ == "__main__":
    print(ingest_gleif_india(Path.cwd()))
