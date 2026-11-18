"""Ingest MCA Company Master Data from data.gov.in official Open Government Data API with checkpointing."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ingest.http_client import PoliteHttpClient
from src.ingest.raw_landing import write_raw_payload
from src.ingest.robots_checker import check_robots

MCA_RESOURCE_ID = "4dbe5667-7b6b-41d7-82af-211562424d9a"
MCA_API_URL = f"https://api.data.gov.in/resource/{MCA_RESOURCE_ID}"
# Official public sample key documented by data.gov.in (rate-limited; override with DATA_GOV_IN_API_KEY)
DEFAULT_SAMPLE_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"


def _checkpoint_path(base_dir: Path, date_str: str) -> Path:
    return base_dir / "data" / "raw" / "mca_company" / date_str / "_checkpoint.json"


def ingest_mca_master(
    base_dir: Path,
    api_key: str | None = None,
    page_size: int = 500,
    max_records: int | None = None,
    resume: bool = True,
    date_str: str | None = None,
) -> dict[str, Any]:
    """Fetch paginated MCA Company Master Data from api.data.gov.in with per-page checkpointing."""
    key = api_key or os.environ.get("DATA_GOV_IN_API_KEY") or DEFAULT_SAMPLE_KEY
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    ckpt_file = _checkpoint_path(base_dir, date_str)
    ckpt_file.parent.mkdir(parents=True, exist_ok=True)

    offset = 0
    page_idx = 0
    fetched_records = 0
    total_available: int | None = None
    downloaded_files: list[str] = []
    failed_pages: list[dict[str, Any]] = []

    if resume and ckpt_file.exists():
        ckpt = json.loads(ckpt_file.read_text(encoding="utf-8"))
        if ckpt.get("completed"):
            return {
                "source": "mca_company",
                "status": "already_completed",
                "resource_id": MCA_RESOURCE_ID,
                "total_available_in_api": ckpt.get("total_available"),
                "fetched_records": ckpt.get("fetched_records", 0),
                "pages_fetched_this_run": 0,
                "failed_pages": ckpt.get("failed_pages", []),
                "checkpoint_file": str(ckpt_file),
            }
        offset = int(ckpt.get("next_offset", 0))
        page_idx = int(ckpt.get("next_page_idx", 0))
        fetched_records = int(ckpt.get("fetched_records", 0))
        total_available = ckpt.get("total_available")
        failed_pages = list(ckpt.get("failed_pages", []))

    stopped_reason: str | None = None

    with PoliteHttpClient(timeout_s=60.0, max_retries=4, backoff_base_s=2.0, min_delay_per_host_s=1.5) as client:
        verdict = check_robots(MCA_API_URL, client=client)
        if not verdict.allowed:
            raise RuntimeError(f"Blocked by robots.txt: {verdict.reason}")

        while max_records is None or fetched_records < max_records:
            limit = page_size if max_records is None else min(page_size, max_records - fetched_records)
            params = {
                "api-key": key,
                "format": "json",
                "offset": offset,
                "limit": limit,
            }
            try:
                resp = client.get(MCA_API_URL, params=params)
            except Exception as exc:
                failed_pages.append({"page_idx": page_idx, "offset": offset, "error": str(exc)})
                stopped_reason = f"Request error at offset={offset}: {exc}"
                break

            if resp.status_code == 429:
                failed_pages.append({"page_idx": page_idx, "offset": offset, "status": 429})
                stopped_reason = f"HTTP 429 rate limit at offset={offset}; checkpoint saved for resume"
                break
            if resp.status_code != 200:
                failed_pages.append({"page_idx": page_idx, "offset": offset, "status": resp.status_code})
                stopped_reason = f"HTTP {resp.status_code} at offset={offset}"
                break

            data = json.loads(resp.text)
            if total_available is None:
                total_available = int(data.get("total", 0))
            records = data.get("records", [])
            if not records:
                break

            filename = f"mca_page_{page_idx:05d}_offset_{offset}.json"
            sanitized_url = f"{MCA_API_URL}?format=json&offset={offset}&limit={limit}"
            path, _ = write_raw_payload(
                base_dir=base_dir,
                source="mca_company",
                filename=filename,
                payload=resp.content,
                source_url=sanitized_url,
                http_status=resp.status_code,
                source_version=str(data.get("updated", "unknown")),
                date_str=date_str,
            )
            downloaded_files.append(str(path))
            fetched_records += len(records)
            offset += len(records)
            page_idx += 1

            completed = total_available is not None and offset >= total_available
            ckpt_file.write_text(
                json.dumps({
                    "next_offset": offset,
                    "next_page_idx": page_idx,
                    "fetched_records": fetched_records,
                    "total_available": total_available,
                    "completed": completed,
                    "failed_pages": failed_pages,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }, indent=2),
                encoding="utf-8",
            )
            if completed:
                break

        if stopped_reason is not None:
            ckpt_file.write_text(
                json.dumps({
                    "next_offset": offset,
                    "next_page_idx": page_idx,
                    "fetched_records": fetched_records,
                    "total_available": total_available,
                    "completed": False,
                    "stopped_reason": stopped_reason,
                    "failed_pages": failed_pages,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }, indent=2),
                encoding="utf-8",
            )

    return {
        "source": "mca_company",
        "resource_id": MCA_RESOURCE_ID,
        "status": "completed" if (total_available and offset >= total_available) else "partial_checkpointed",
        "total_available_in_api": total_available,
        "fetched_records": fetched_records,
        "pages_this_run": len(downloaded_files),
        "failed_pages": failed_pages,
        "stopped_reason": stopped_reason,
        "robots_allowed": verdict.allowed,
        "checkpoint_file": str(ckpt_file),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--page-size", type=int, default=500)
    parser.add_argument("--max-records", type=int, default=None)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()
    print(json.dumps(
        ingest_mca_master(
            Path.cwd(),
            page_size=args.page_size,
            max_records=args.max_records,
            resume=not args.no_resume,
        ),
        indent=2,
    ))
