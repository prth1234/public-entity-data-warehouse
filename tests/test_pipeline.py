"""Unit and integration tests for validators, transforms, raw landing, and DuckDB idempotency."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.ingest.raw_landing import write_raw_payload
from src.transform.pincode import backfill_branch_pincodes, transform_pincode_directory
from src.transform.standardise import extract_pincode, normalise_state
import pandas as pd
from src.validate.schema_drift import check_schema_drift
from src.validate.validators import (
    IfscBranchRecord,
    compute_gstin_checksum,
    parse_cin,
    parse_gstin,
    validate_gstin_checksum,
)
from warehouse.load_warehouse import run_warehouse_load


def test_ifsc_validator() -> None:
    rec = IfscBranchRecord(
        ifsc="sbin0000001",
        bank_code="SBIN",
        branch_name="KOLKATA MAIN",
        pincode="700001",
    )
    assert rec.ifsc == "SBIN0000001"

    with pytest.raises(ValueError):
        IfscBranchRecord(ifsc="INVALID123", bank_code="INVA", branch_name="BAD")


def test_parse_cin() -> None:
    parsed = parse_cin("U27900GJ2025PTC166696")
    assert parsed.listing_status == "U"
    assert parsed.industry_code == "27900"
    assert parsed.state_code == "GJ"
    assert parsed.incorporation_year == 2025
    assert parsed.ownership_type == "PTC"
    assert parsed.registration_number == "166696"

    with pytest.raises(ValueError):
        parse_cin("BAD_CIN")


def test_gstin_checksum_and_parse() -> None:
    prefix = "24AABCE1234F1Z"
    chk = compute_gstin_checksum(prefix)
    gstin = prefix + chk
    assert validate_gstin_checksum(gstin) is True
    parsed = parse_gstin(gstin)
    assert parsed.state_code == "24"
    assert parsed.pan_segment == "AABCE1234F"
    assert parsed.entity_number == "1"
    assert parsed.checksum_valid is True

    # Corrupt last char
    bad_char = "0" if chk != "0" else "1"
    assert validate_gstin_checksum(prefix + bad_char) is False


def test_normalise_state_and_pincode() -> None:
    assert normalise_state("gujarat") == "GUJARAT"
    assert normalise_state("Orissa") == "ODISHA"
    assert normalise_state(None, iso_hint="IN-WB") == "WEST BENGAL"
    assert extract_pincode("1 STRAND ROAD, KOLKATA 700001") == "700001"
    assert extract_pincode("NO PINCODE HERE") is None


def test_schema_drift() -> None:
    rep_ok = check_schema_drift("test", {"a", "b"}, {"a", "b", "c"})
    assert rep_ok.has_breaking_drift is False
    assert rep_ok.unexpected_columns == {"c"}

    rep_bad = check_schema_drift("test", {"a", "b"}, {"a"})
    assert rep_bad.has_breaking_drift is True
    assert rep_bad.missing_columns == {"b"}


def test_raw_landing_writer(tmp_path: Path) -> None:
    payload = b'{"hello": "world"}'
    p_path, m_path = write_raw_payload(
        base_dir=tmp_path,
        source="unit_test",
        filename="sample.json",
        payload=payload,
        source_url="https://example.org/sample.json",
        http_status=200,
        source_version="v1",
        date_str="2026-11-18",
    )
    assert p_path.read_bytes() == payload
    meta = json.loads(m_path.read_text(encoding="utf-8"))
    assert meta["checksum_sha256"] == hashlib.sha256(payload).hexdigest()
    assert meta["http_status"] == 200
    assert meta["source_version"] == "v1"


def test_warehouse_idempotency() -> None:
    root = Path.cwd()
    res1 = run_warehouse_load(root)
    res2 = run_warehouse_load(root)
    assert res2["scd_inserts_this_run"] == 0
    assert res1["warehouse_counts"] == res2["warehouse_counts"]
    assert res2["warehouse_counts"]["dim_bank_branch"] >= 180000
    assert res2["warehouse_counts"]["dim_company"] >= 30
    assert res2["warehouse_counts"]["dim_pincode"] >= 19000
    assert res2["warehouse_counts"]["dim_lei"] >= 10000


def test_pincode_transform_and_backfill(tmp_path: Path) -> None:
    csv_bytes = (
        b'"CircleName","RegionName","DivisionName","OfficeName","Pincode","OfficeType","Delivery","District","StateName","Latitude","Longitude"\n'
        b'"Gujarat Circle","Vadodara","Vadodara","Alkapuri S.O","390007","SO","Delivery","VADODARA","GUJARAT","22.3","73.1"\n'
        b'"Gujarat Circle","Vadodara","Vadodara","Bad Pin","99999","SO","Delivery","VADODARA","GUJARAT","22.3","73.1"\n'
    )
    write_raw_payload(
        base_dir=tmp_path,
        source="india_post_pincode",
        filename="pincode.csv",
        payload=csv_bytes,
        source_url="https://example.org/pincode.csv",
        http_status=200,
        source_version="test",
        date_str="2026-11-18",
    )
    pin_df, metrics = transform_pincode_directory(tmp_path / "data" / "raw" / "india_post_pincode" / "2026-11-18")
    assert metrics["unique_pincodes"] == 1
    assert metrics["invalid_pincode_dropped"] == 1

    ifsc_df = pd.DataFrame([
        {"ifsc": "SBIN0000001", "state_name": "GUJARAT", "district": "VADODARA", "pincode": "390001"},
        {"ifsc": "SBIN0000002", "state_name": "GUJARAT", "district": "VADODARA", "pincode": None},
        {"ifsc": "SBIN0000003", "state_name": "GUJARAT", "district": "UNKNOWN_DIST", "pincode": None},
    ])
    filled_df, stats = backfill_branch_pincodes(ifsc_df, pin_df)
    assert stats["filled_from_district"] == 1
    assert filled_df.loc[0, "pincode_source"] == "original"
    assert filled_df.loc[1, "pincode"] == "390007"
    assert filled_df.loc[1, "pincode_source"] == "inferred_from_district"
    assert pd.isna(filled_df.loc[2, "pincode_source"])
