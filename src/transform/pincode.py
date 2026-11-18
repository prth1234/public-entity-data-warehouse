"""Normalise India Post pincode directory and backfill missing bank-branch pincodes."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from src.transform.standardise import normalise_state, normalise_text
from src.validate.schema_drift import check_schema_drift

PINCODE_6_RE = re.compile(r"^\d{6}$")


def transform_pincode_directory(raw_dir: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Clean and normalise pincode.csv into dim_pincode (6-digit numeric pincode PK)."""
    csv_path = raw_dir / "pincode.csv"
    meta = json.loads((raw_dir / "pincode.csv.meta.json").read_text(encoding="utf-8"))

    df = pd.read_csv(csv_path, dtype=str, keep_default_na=True)
    drift = check_schema_drift(
        "india_post_pincode",
        {"Pincode", "StateName", "District", "OfficeName"},
        df.columns,
    )
    if drift.has_breaking_drift:
        raise ValueError(f"Breaking schema drift in pincode.csv: missing {drift.missing_columns}")

    raw_rows = len(df)
    df["pincode"] = df["Pincode"].astype(str).str.strip()
    valid_mask = df["pincode"].str.match(PINCODE_6_RE, na=False)
    invalid_dropped = int((~valid_mask).sum())
    df = df[valid_mask].copy()

    df["state_name"] = df["StateName"].apply(normalise_state)
    df["district"] = df["District"].apply(lambda v: normalise_text(v).upper() if normalise_text(v) else None)
    df["office_name"] = df["OfficeName"].apply(normalise_text)

    # Aggregate to unique 6-digit pincode (representative office + count of post offices)
    office_counts = df.groupby("pincode")["office_name"].transform("count")
    df["office_count"] = office_counts
    deduped = df.drop_duplicates(subset=["pincode"], keep="first").copy()
    deduped["source"] = "india_post_pincode"
    deduped["ingested_at"] = meta["fetched_at"]
    deduped["source_version"] = meta["source_version"]

    out_cols = [
        "pincode",
        "state_name",
        "district",
        "office_name",
        "office_count",
        "source",
        "ingested_at",
        "source_version",
    ]
    out_df = deduped[out_cols].reset_index(drop=True)
    metrics = {
        "source": "india_post_pincode",
        "raw_rows": raw_rows,
        "unique_pincodes": len(out_df),
        "invalid_pincode_dropped": invalid_dropped,
        "null_rate_state_name": round(float(out_df["state_name"].isna().mean()), 4),
        "null_rate_district": round(float(out_df["district"].isna().mean()), 4),
    }
    return out_df, metrics


def backfill_branch_pincodes(
    ifsc_df: pd.DataFrame, pincode_df: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fill missing IFSC pincodes via normalised (state_name, district) and tag pincode_source."""
    df = ifsc_df.copy()
    has_orig = df["pincode"].notna() & df["pincode"].astype(str).str.match(PINCODE_6_RE, na=False)
    missing_before = int((~has_orig).sum())

    # Representative pincode per (state_name, district) from dim_pincode
    valid_pin = pincode_df.dropna(subset=["state_name", "district", "pincode"])
    dist_map = (
        valid_pin.drop_duplicates(subset=["state_name", "district"], keep="first")
        .set_index(["state_name", "district"])["pincode"]
        .to_dict()
    )

    df["pincode_source"] = None
    df.loc[has_orig, "pincode_source"] = "original"

    dist_upper = df["district"].apply(lambda v: v.strip().upper() if isinstance(v, str) else None)
    inferred_vals = [
        dist_map.get((st, dt)) if not orig else None
        for orig, st, dt in zip(has_orig, df["state_name"], dist_upper)
    ]
    inferred_series = pd.Series(inferred_vals, index=df.index)
    filled_mask = (~has_orig) & inferred_series.notna()

    df.loc[filled_mask, "pincode"] = inferred_series[filled_mask]
    df.loc[filled_mask, "pincode_source"] = "inferred_from_district"

    filled_count = int(filled_mask.sum())
    still_missing = int(df["pincode"].isna().sum())
    stats = {
        "total_branches": len(df),
        "missing_before": missing_before,
        "filled_from_district": filled_count,
        "still_missing_after": still_missing,
        "fill_rate_pct": round((filled_count / missing_before * 100.0), 2) if missing_before else 0.0,
    }
    return df, stats
