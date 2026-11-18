"""Immutable raw-landing zone writer with SHA-256 checksums and provenance metadata."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class RawArtifactMetadata:
    source: str
    source_url: str
    fetched_at: str
    checksum_sha256: str
    http_status: int
    byte_size: int
    filename: str
    source_version: str


def write_raw_payload(
    *,
    base_dir: Path,
    source: str,
    filename: str,
    payload: bytes,
    source_url: str,
    http_status: int,
    source_version: str = "unversioned",
    date_str: str | None = None,
) -> tuple[Path, Path]:
    """Write untouched payload and sidecar metadata JSON to data/raw/<source>/<date>/."""
    now = datetime.now(timezone.utc)
    if date_str is None:
        date_str = now.strftime("%Y-%m-%d")

    landing_dir = base_dir / "data" / "raw" / source / date_str
    landing_dir.mkdir(parents=True, exist_ok=True)

    payload_path = landing_dir / filename
    payload_path.write_bytes(payload)

    checksum = hashlib.sha256(payload).hexdigest()
    meta = RawArtifactMetadata(
        source=source,
        source_url=source_url,
        fetched_at=now.isoformat(),
        checksum_sha256=checksum,
        http_status=http_status,
        byte_size=len(payload),
        filename=filename,
        source_version=source_version,
    )
    meta_path = landing_dir / f"{filename}.meta.json"
    meta_path.write_text(json.dumps(asdict(meta), indent=2), encoding="utf-8")
    return payload_path, meta_path
