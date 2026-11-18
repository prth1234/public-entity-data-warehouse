"""Ingest MCA Company Master Data from data.gov.in official Open Government Data API."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.ingest.http_client import PoliteHttpClient
from src.ingest.raw_landing import write_raw_payload
from src.ingest.robots_checker import check_robots

MCA_RESOURCE_ID = "4dbe5667-7b6b-41d7-82af-211562424d9a"
MCA_API_URL = f"https://api.data.gov.in/resource/{MCA_RESOURCE_ID}"
# Official public sample key documented by data.gov.in (rate-limited; override with DATA_GOV_IN_API_KEY)
DEFAULT_SAMPLE_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"


def ingest_mca_master(
    base_dir: Path,
    api_key: str | None = None,
    page_size: int = 100,
    max_records: int = 300,
) -> dict[str, Any]:
    """Fetch paginated MCA Company Master Data from api.data.gov.in into data/raw/mca_company/."""
    key = api_key or os.environ.get("DATA_GOV_IN_API_KEY") or DEFAULT_SAMPLE_KEY
    downloaded_files: list[str] = []
    total_available: int | None = None
    fetched_records = 0

    with PoliteHttpClient(timeout_s=60.0, max_retries=4, backoff_base_s=2.0, min_delay_per_host_s=1.5) as client:
        verdict = check_robots(MCA_API_URL, client=client)
        if not verdict.allowed:
            raise RuntimeError(f"Blocked by robots.txt: {verdict.reason}")

        offset = 0
        page_idx = 0
        while fetched_records < max_records:
            limit = min(page_size, max_records - fetched_records)
            params = {
                "api-key": key,
                "format": "json",
                "offset": offset,
                "limit": limit,
            }
            resp = client.get(MCA_API_URL, params=params)
            if resp.status_code == 429 and downloaded_files:
                # Sample key is strictly rate-limited; preserve already landed pages.
                break
            if resp.status_code != 200:
                raise RuntimeError(
                    f"data.gov.in API returned HTTP {resp.status_code} at offset={offset}: {resp.text[:300]}"
                )

            data = json.loads(resp.text)
            if total_available is None:
                total_available = int(data.get("total", 0))
            records = data.get("records", [])
            if not records:
                break

            filename = f"mca_page_{page_idx:04d}_offset_{offset}.json"
            sanitized_url = f"{MCA_API_URL}?format=json&offset={offset}&limit={limit}"
            path, _ = write_raw_payload(
                base_dir=base_dir,
                source="mca_company",
                filename=filename,
                payload=resp.content,
                source_url=sanitized_url,
                http_status=resp.status_code,
                source_version=str(data.get("updated", "unknown")),
            )
            downloaded_files.append(str(path))
            fetched_records += len(records)
            offset += len(records)
            page_idx += 1

            if len(records) == 0:
                break

    return {
        "source": "mca_company",
        "resource_id": MCA_RESOURCE_ID,
        "total_available_in_api": total_available,
        "fetched_records": fetched_records,
        "pages": len(downloaded_files),
        "robots_allowed": verdict.allowed,
        "files": downloaded_files,
    }


if __name__ == "__main__":
    print(ingest_mca_master(Path.cwd(), page_size=10, max_records=50))
