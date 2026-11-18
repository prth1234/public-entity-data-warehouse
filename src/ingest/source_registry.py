"""Source registry loader and validator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SourceEntry:
    source_id: str
    name: str
    owner: str
    url: str
    license: str
    auth_type: str
    refresh_cadence: str
    access_date: str
    robots_verdict: str
    tos_verdict: str
    status: str
    notes: str = ""


def load_source_registry(path: Path) -> dict[str, SourceEntry]:
    """Load source registry YAML into a dict keyed by source_id."""
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries: dict[str, SourceEntry] = {}
    for source_id, item in (raw.get("sources") or {}).items():
        entries[source_id] = SourceEntry(
            source_id=source_id,
            name=item["name"],
            owner=item["owner"],
            url=item["url"],
            license=item["license"],
            auth_type=item["auth_type"],
            refresh_cadence=item["refresh_cadence"],
            access_date=str(item["access_date"]),
            robots_verdict=item["robots_verdict"],
            tos_verdict=item["tos_verdict"],
            status=item["status"],
            notes=item.get("notes", ""),
        )
    return entries
