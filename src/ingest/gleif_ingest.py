"""Ingest Indian Legal Entity Identifier (LEI) records from official GLEIF API (CC0 public domain)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ingest.http_client import PoliteHttpClient
from src.ingest.raw_landing import write_raw_payload
from src.ingest.robots_checker import check_robots

GLEIF_START_URL = (
    "https://api.gleif.org/api/v1/lei-records"
    "?filter%5Bentity.legalAddress.country%5D=IN&page%5Bsize%5D=200"
)


def _checkpoint_path(base_dir: Path, date_str: str) -> Path:
    return base_dir / "data" / "raw" / "gleif_lei" / date_str / "_checkpoint.json"


def ingest_gleif_india(
    base_dir: Path,
    max_pages: int | None = None,
    resume: bool = True,
    max_consecutive_errors: int = 5,
    date_str: str | None = None,
) -> dict[str, Any]:
    """Paginate through all Indian LEI records following links.next with checkpointing."""
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    ckpt_file = _checkpoint_path(base_dir, date_str)
    ckpt_file.parent.mkdir(parents=True, exist_ok=True)

    next_url: str | None = GLEIF_START_URL
    page_num = 1
    fetched_records = 0
    total_available: int | None = None
    downloaded_files: list[str] = []

    if resume and ckpt_file.exists():
        ckpt = json.loads(ckpt_file.read_text(encoding="utf-8"))
        if ckpt.get("completed"):
            return {
                "source": "gleif_lei",
                "status": "already_completed",
                "total_available_in_api": ckpt.get("total_available"),
                "fetched_records": ckpt.get("fetched_records", 0),
                "pages_fetched_this_run": 0,
                "checkpoint_file": str(ckpt_file),
            }
        next_url = ckpt.get("next_url", GLEIF_START_URL)
        page_num = int(ckpt.get("page_num", 1))
        fetched_records = int(ckpt.get("fetched_records", 0))
        total_available = ckpt.get("total_available")

    consecutive_errors = 0
    pages_this_run = 0
    stopped_reason: str | None = None

    with PoliteHttpClient(timeout_s=30.0, max_retries=3, backoff_base_s=1.0, min_delay_per_host_s=0.5) as client:
        verdict = check_robots(GLEIF_START_URL, client=client)
        if not verdict.allowed:
            raise RuntimeError(f"Blocked by robots.txt: {verdict.reason}")

        while next_url is not None:
            if max_pages is not None and pages_this_run >= max_pages:
                stopped_reason = f"Reached max_pages={max_pages}"
                break

            try:
                resp = client.get(next_url)
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")

                data = json.loads(resp.text)
                consecutive_errors = 0
            except Exception as exc:
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    stopped_reason = f"Stopped after {consecutive_errors} consecutive errors: {exc}"
                    ckpt_file.write_text(
                        json.dumps({
                            "next_url": next_url,
                            "page_num": page_num,
                            "fetched_records": fetched_records,
                            "total_available": total_available,
                            "completed": False,
                            "last_error": str(exc),
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }, indent=2),
                        encoding="utf-8",
                    )
                    break
                continue

            if total_available is None:
                total_available = int(data.get("meta", {}).get("pagination", {}).get("total", 0))

            records = data.get("data", [])
            if not records:
                next_url = None
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
                date_str=date_str,
            )
            downloaded_files.append(str(path))
            fetched_records += len(records)
            pages_this_run += 1

            next_url = (data.get("links") or {}).get("next")
            page_num += 1

            ckpt_file.write_text(
                json.dumps({
                    "next_url": next_url,
                    "page_num": page_num,
                    "fetched_records": fetched_records,
                    "total_available": total_available,
                    "completed": next_url is None,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }, indent=2),
                encoding="utf-8",
            )

    return {
        "source": "gleif_lei",
        "status": "completed" if next_url is None else "partial_checkpointed",
        "total_available_in_api": total_available,
        "fetched_records": fetched_records,
        "pages_fetched_this_run": pages_this_run,
        "robots_allowed": verdict.allowed,
        "stopped_reason": stopped_reason,
        "checkpoint_file": str(ckpt_file),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()
    print(json.dumps(
        ingest_gleif_india(Path.cwd(), max_pages=args.max_pages, resume=not args.no_resume),
        indent=2,
    ))
