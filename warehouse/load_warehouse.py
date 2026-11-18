"""Load cleaned staging data into DuckDB warehouse with idempotent upserts & SCD Type 2."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.transform.standardise import (
    build_state_dim_df,
    build_validated_gstin_fixture_df,
    transform_gst_hsn_sac,
    transform_ifsc,
    transform_mca,
)


def latest_raw_date_dir(base_dir: Path, source: str) -> Path:
    source_root = base_dir / "data" / "raw" / source
    date_dirs = sorted([d for d in source_root.iterdir() if d.is_dir()])
    if not date_dirs:
        raise FileNotFoundError(f"No raw landing directories found under {source_root}")
    return date_dirs[-1]


def _record_hash(row: pd.Series) -> str:
    payload = "|".join([
        str(row.get("company_status") or ""),
        str(row.get("registered_address") or ""),
        str(row.get("paidup_capital") or ""),
    ])
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def run_warehouse_load(base_dir: Path, db_path: Path | None = None) -> dict[str, Any]:
    """Run transforms on latest raw data and load DuckDB warehouse idempotently."""
    if db_path is None:
        db_path = base_dir / "warehouse" / "zintrl.duckdb"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    ifsc_dir = latest_raw_date_dir(base_dir, "rbi_ifsc")
    mca_dir = latest_raw_date_dir(base_dir, "mca_company")
    gst_dir = latest_raw_date_dir(base_dir, "gst_masters")

    state_df = build_state_dim_df()
    ifsc_df, ifsc_metrics = transform_ifsc(ifsc_dir)
    mca_df, mca_metrics = transform_mca(mca_dir)
    hsn_df, hsn_metrics = transform_gst_hsn_sac(gst_dir)
    gstin_df = build_validated_gstin_fixture_df()

    # Map state_name -> gst_state_code
    state_map = dict(zip(state_df["state_name"], state_df["gst_state_code"]))
    ifsc_df["gst_state_code"] = ifsc_df["state_name"].map(state_map)
    mca_df["gst_state_code"] = mca_df["state_name"].map(state_map)

    con = duckdb.connect(str(db_path))
    ddl_sql = (base_dir / "warehouse" / "ddl.sql").read_text(encoding="utf-8")
    con.execute(ddl_sql)

    # Register staging frames
    con.register("stg_state_df", state_df)
    con.register("stg_ifsc_df", ifsc_df)
    con.register("stg_mca_df", mca_df)
    con.register("stg_hsn_df", hsn_df)
    con.register("stg_gstin_df", gstin_df)

    # Materialise raw_staging tables
    con.execute("CREATE OR REPLACE TABLE raw_staging.stg_ifsc AS SELECT * FROM stg_ifsc_df")
    con.execute("CREATE OR REPLACE TABLE raw_staging.stg_mca AS SELECT * FROM stg_mca_df")
    con.execute("CREATE OR REPLACE TABLE raw_staging.stg_hsn_sac AS SELECT * FROM stg_hsn_df")
    con.execute("CREATE OR REPLACE TABLE raw_staging.stg_gstin AS SELECT * FROM stg_gstin_df")

    # Idempotent dimension loads
    con.execute("INSERT OR REPLACE INTO warehouse.dim_state SELECT * FROM stg_state_df")
    con.execute("""
        INSERT OR REPLACE INTO warehouse.dim_bank_branch
        SELECT
            ifsc, bank_code, bank_name, branch_name, address, city, district,
            state_name, gst_state_code, pincode, micr, neft, rtgs, imps, upi,
            source, ingested_at, source_version
        FROM stg_ifsc_df
    """)
    con.execute("INSERT OR REPLACE INTO warehouse.dim_gstin SELECT * FROM stg_gstin_df")
    con.execute("INSERT OR REPLACE INTO warehouse.dim_hsn_sac SELECT * FROM stg_hsn_df")

    # SCD Type 2 for warehouse.dim_company
    mca_df["record_hash"] = mca_df.apply(_record_hash, axis=1)
    existing_current = con.execute(
        "SELECT cin, record_hash FROM warehouse.dim_company WHERE is_current = TRUE"
    ).fetchdf()
    existing_map = dict(zip(existing_current["cin"], existing_current["record_hash"]))

    scd_inserts = []
    closed_cins = []
    for _, row in mca_df.iterrows():
        cin = row["cin"]
        rhash = row["record_hash"]
        if cin in existing_map and existing_map[cin] == rhash:
            continue  # Idempotent: unchanged
        if cin in existing_map:
            closed_cins.append((row["ingested_at"], cin))
        sk = hashlib.sha256(f"{cin}|{rhash}|{row['ingested_at']}".encode("utf-8")).hexdigest()[:24]
        scd_inserts.append({
            "company_sk": sk,
            "cin": cin,
            "company_name": row["company_name"],
            "company_status": row["company_status"],
            "listing_status": row["listing_status"],
            "industry_code": row["industry_code"],
            "cin_state_code": row["cin_state_code"],
            "incorporation_year": int(row["incorporation_year"]),
            "ownership_type": row["ownership_type"],
            "registration_number": row["registration_number"],
            "roc_code": row["roc_code"],
            "company_category": row["company_category"],
            "company_class": row["company_class"],
            "industrial_classification": row["industrial_classification"],
            "authorized_capital": row["authorized_capital"],
            "paidup_capital": row["paidup_capital"],
            "registration_date": row["registration_date"],
            "registered_address": row["registered_address"],
            "state_name": row["state_name"],
            "gst_state_code": row["gst_state_code"],
            "pincode": row["pincode"],
            "record_hash": rhash,
            "valid_from": row["ingested_at"],
            "valid_to": "9999-12-31T23:59:59+00:00",
            "is_current": True,
            "source": row["source"],
            "ingested_at": row["ingested_at"],
            "source_version": row["source_version"],
        })

    for valid_to_ts, cin in closed_cins:
        con.execute(
            "UPDATE warehouse.dim_company SET is_current = FALSE, valid_to = ? WHERE cin = ? AND is_current = TRUE",
            [valid_to_ts, cin],
        )

    if scd_inserts:
        scd_df = pd.DataFrame(scd_inserts)
        con.register("scd_df", scd_df)
        con.execute("INSERT INTO warehouse.dim_company SELECT * FROM scd_df")

    # Facts
    snapshot_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    con.execute(
        f"""
        INSERT OR REPLACE INTO warehouse.fact_company_status_snapshot
        SELECT
            '{snapshot_date}' AS snapshot_date,
            cin, gst_state_code, company_status, authorized_capital, paidup_capital,
            source, ingested_at, source_version
        FROM stg_mca_df
        """
    )
    con.execute(
        f"""
        INSERT OR REPLACE INTO warehouse.fact_gst_registration
        SELECT
            gstin, gst_state_code, pan_segment, registration_status, checksum_valid,
            '{snapshot_date}' AS snapshot_date,
            source, ingested_at, source_version
        FROM stg_gstin_df
        """
    )

    counts = {
        "dim_state": con.execute("SELECT COUNT(*) FROM warehouse.dim_state").fetchone()[0],
        "dim_bank_branch": con.execute("SELECT COUNT(*) FROM warehouse.dim_bank_branch").fetchone()[0],
        "dim_company": con.execute("SELECT COUNT(*) FROM warehouse.dim_company").fetchone()[0],
        "dim_gstin": con.execute("SELECT COUNT(*) FROM warehouse.dim_gstin").fetchone()[0],
        "dim_hsn_sac": con.execute("SELECT COUNT(*) FROM warehouse.dim_hsn_sac").fetchone()[0],
        "fact_company_status_snapshot": con.execute("SELECT COUNT(*) FROM warehouse.fact_company_status_snapshot").fetchone()[0],
        "fact_gst_registration": con.execute("SELECT COUNT(*) FROM warehouse.fact_gst_registration").fetchone()[0],
    }
    con.close()

    return {
        "db_path": str(db_path),
        "metrics": {
            "ifsc": ifsc_metrics,
            "mca": mca_metrics,
            "hsn_sac": hsn_metrics,
        },
        "warehouse_counts": counts,
        "scd_inserts_this_run": len(scd_inserts),
    }


if __name__ == "__main__":
    print(json.dumps(run_warehouse_load(Path.cwd()), indent=2))
