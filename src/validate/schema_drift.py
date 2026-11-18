"""Schema-drift detection for raw ingested files."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class SchemaDriftReport:
    source: str
    expected_columns: set[str]
    actual_columns: set[str]
    missing_columns: set[str]
    unexpected_columns: set[str]
    has_breaking_drift: bool


def check_schema_drift(
    source: str,
    expected_columns: Iterable[str],
    actual_columns: Iterable[str],
) -> SchemaDriftReport:
    """Compare observed columns against expected contract; flag missing columns as breaking."""
    exp = set(expected_columns)
    act = set(actual_columns)
    missing = exp - act
    unexpected = act - exp
    return SchemaDriftReport(
        source=source,
        expected_columns=exp,
        actual_columns=act,
        missing_columns=missing,
        unexpected_columns=unexpected,
        has_breaking_drift=len(missing) > 0,
    )
