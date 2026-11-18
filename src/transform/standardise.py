"""Cleaning and standardisation transforms for IFSC, MCA, GST/HSN, and State Reference."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.validate.schema_drift import check_schema_drift
from src.validate.validators import IFSC_RE, parse_cin, parse_gstin

PINCODE_RE = re.compile(r"\b([1-8][0-9]{5})\b")
MULTI_SPACE_RE = re.compile(r"\s+")

# Authoritative Indian State/UT Master: (gst_state_code, iso_mca_code, canonical_name)
STATE_MASTER: list[tuple[str, str, str]] = [
    ("01", "JK", "JAMMU AND KASHMIR"),
    ("02", "HP", "HIMACHAL PRADESH"),
    ("03", "PB", "PUNJAB"),
    ("04", "CH", "CHANDIGARH"),
    ("05", "UK", "UTTARAKHAND"),
    ("06", "HR", "HARYANA"),
    ("07", "DL", "DELHI"),
    ("08", "RJ", "RAJASTHAN"),
    ("09", "UP", "UTTAR PRADESH"),
    ("10", "BR", "BIHAR"),
    ("11", "SK", "SIKKIM"),
    ("12", "AR", "ARUNACHAL PRADESH"),
    ("13", "NL", "NAGALAND"),
    ("14", "MN", "MANIPUR"),
    ("15", "MZ", "MIZORAM"),
    ("16", "TR", "TRIPURA"),
    ("17", "ML", "MEGHALAYA"),
    ("18", "AS", "ASSAM"),
    ("19", "WB", "WEST BENGAL"),
    ("20", "JH", "JHARKHAND"),
    ("21", "OD", "ODISHA"),
    ("22", "CG", "CHHATTISGARH"),
    ("23", "MP", "MADHYA PRADESH"),
    ("24", "GJ", "GUJARAT"),
    ("26", "DN", "DADRA AND NAGAR HAVELI AND DAMAN AND DIU"),
    ("27", "MH", "MAHARASHTRA"),
    ("29", "KA", "KARNATAKA"),
    ("30", "GA", "GOA"),
    ("31", "LD", "LAKSHADWEEP"),
    ("32", "KL", "KERALA"),
    ("33", "TN", "TAMIL NADU"),
    ("34", "PY", "PUDUCHERRY"),
    ("35", "AN", "ANDAMAN AND NICOBAR ISLANDS"),
    ("36", "TG", "TELANGANA"),
    ("37", "AP", "ANDHRA PRADESH"),
    ("38", "LA", "LADAKH"),
]

STATE_ALIAS_TO_CANONICAL: dict[str, str] = {
    name: name for _, _, name in STATE_MASTER
}
STATE_ALIAS_TO_CANONICAL.update({
    "ORISSA": "ODISHA",
    "UTTARANCHAL": "UTTARAKHAND",
    "PONDICHERRY": "PUDUCHERRY",
    "NCT OF DELHI": "DELHI",
    "NEW DELHI": "DELHI",
    "DAMAN AND DIU": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "DADRA AND NAGAR HAVELI": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "DADRA & NAGAR HAVELI": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "ANDAMAN & NICOBAR ISLANDS": "ANDAMAN AND NICOBAR ISLANDS",
    "ANDAMAN AND NICOBAR": "ANDAMAN AND NICOBAR ISLANDS",
    "JAMMU & KASHMIR": "JAMMU AND KASHMIR",
    "CHATTISGARH": "CHHATTISGARH",
    "TELENGANA": "TELANGANA",
})
ISO_TO_CANONICAL: dict[str, str] = {iso: name for _, iso, name in STATE_MASTER}
ISO_TO_CANONICAL["OR"] = "ODISHA"
ISO_TO_CANONICAL["TS"] = "TELANGANA"
ISO_TO_CANONICAL["UA"] = "UTTARAKHAND"


def normalise_text(val: Any) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = MULTI_SPACE_RE.sub(" ", str(val).strip())
    return s if s and s.upper() not in {"NA", "NULL", "NONE", "NAN"} else None


def normalise_state(raw_state: Any, iso_hint: str | None = None) -> str | None:
    s = normalise_text(raw_state)
    if s:
        up = s.upper().replace("&", "AND")
        up = MULTI_SPACE_RE.sub(" ", up)
        if up in STATE_ALIAS_TO_CANONICAL:
            return STATE_ALIAS_TO_CANONICAL[up]
    if iso_hint:
        code = iso_hint.strip().upper().replace("IN-", "")
        if code in ISO_TO_CANONICAL:
            return ISO_TO_CANONICAL[code]
    return s.upper() if s else None


def extract_pincode(address: Any) -> str | None:
    if not isinstance(address, str) or not address:
        return None
    matches = PINCODE_RE.findall(address)
    return matches[-1] if matches else None


def normalise_status(status: Any) -> str:
    s = normalise_text(status)
    if not s:
        return "UNKNOWN"
    return s.upper().replace(" ", "_")


def build_state_dim_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "gst_state_code": gst_code,
                "iso_state_code": iso_code,
                "state_name": name,
            }
            for gst_code, iso_code, name in STATE_MASTER
        ]
    )


def transform_ifsc(raw_dir: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Clean, validate, enrich (via banks.json), and deduplicate RBI IFSC master."""
    ifsc_path = raw_dir / "IFSC.csv"
    banks_path = raw_dir / "banks.json"
    meta_path = raw_dir / "IFSC.csv.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    banks_map: dict[str, str] = {}
    if banks_path.exists():
        banks_raw = json.loads(banks_path.read_text(encoding="utf-8"))
        for code, info in banks_raw.items():
            if isinstance(info, dict) and info.get("name"):
                banks_map[code.upper()] = info["name"]
            elif isinstance(info, str):
                banks_map[code.upper()] = info

    df = pd.read_csv(ifsc_path, dtype=str, keep_default_na=True)
    drift = check_schema_drift(
        "rbi_ifsc",
        {"BANK", "IFSC", "BRANCH", "CENTRE", "DISTRICT", "STATE", "ADDRESS", "IMPS", "RTGS", "CITY", "ISO3166", "NEFT", "MICR", "UPI"},
        df.columns,
    )
    if drift.has_breaking_drift:
        raise ValueError(f"Breaking schema drift in IFSC.csv: missing {drift.missing_columns}")

    raw_rows = len(df)
    df["ifsc"] = df["IFSC"].astype(str).str.strip().str.upper()
    df["ifsc_valid"] = df["ifsc"].apply(lambda x: bool(IFSC_RE.match(x)))
    invalid_ifsc_count = int((~df["ifsc_valid"]).sum())
    df = df[df["ifsc_valid"]].copy()

    dup_count = int(df.duplicated(subset=["ifsc"]).sum())
    df = df.drop_duplicates(subset=["ifsc"], keep="first").copy()

    df["bank_code"] = df["ifsc"].str[:4]
    df["bank_name"] = df.apply(
        lambda r: normalise_text(r["BANK"]) or banks_map.get(r["bank_code"]),
        axis=1,
    )
    df["branch_name"] = df["BRANCH"].apply(normalise_text)
    df["address"] = df["ADDRESS"].apply(normalise_text)
    df["city"] = df["CITY"].apply(normalise_text)
    df["district"] = df["DISTRICT"].apply(normalise_text)
    df["state_name"] = df.apply(
        lambda r: normalise_state(r["STATE"], normalise_text(r.get("ISO3166"))),
        axis=1,
    )
    df["pincode"] = df["address"].apply(extract_pincode)
    df["micr"] = df["MICR"].apply(
        lambda v: normalise_text(v).split(".")[0] if normalise_text(v) else None
    )

    for flag in ("NEFT", "RTGS", "IMPS", "UPI"):
        df[flag.lower()] = df[flag].astype(str).str.strip().str.lower().isin({"true", "1", "yes"})

    df["source"] = "rbi_ifsc_razorpay"
    df["ingested_at"] = meta["fetched_at"]
    df["source_version"] = meta["source_version"]

    out_cols = [
        "ifsc", "bank_code", "bank_name", "branch_name", "address",
        "city", "district", "state_name", "pincode", "micr",
        "neft", "rtgs", "imps", "upi",
        "source", "ingested_at", "source_version",
    ]
    out_df = df[out_cols].reset_index(drop=True)
    metrics = {
        "source": "rbi_ifsc",
        "raw_rows": raw_rows,
        "clean_rows": len(out_df),
        "invalid_ifsc_dropped": invalid_ifsc_count,
        "duplicates_dropped": dup_count,
        "null_rate_bank_name": round(float(out_df["bank_name"].isna().mean()), 4),
        "null_rate_pincode": round(float(out_df["pincode"].isna().mean()), 4),
        "null_rate_state_name": round(float(out_df["state_name"].isna().mean()), 4),
    }
    return out_df, metrics


def transform_mca(raw_dir: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Clean, parse CIN components, normalise, and deduplicate MCA Company Master records."""
    records: list[dict[str, Any]] = []
    meta_latest: dict[str, Any] = {}
    for page_file in sorted(raw_dir.glob("mca_page_*.json")):
        payload = json.loads(page_file.read_text(encoding="utf-8"))
        meta_file = raw_dir / f"{page_file.name}.meta.json"
        if meta_file.exists():
            meta_latest = json.loads(meta_file.read_text(encoding="utf-8"))
        records.extend(payload.get("records", []))

    if not records:
        raise ValueError(f"No MCA records found in {raw_dir}")

    df = pd.DataFrame(records)
    drift = check_schema_drift(
        "mca_company",
        {"CIN", "CompanyName", "CompanyStatus", "CompanyROCcode", "Registered_Office_Address", "CompanyStateCode"},
        df.columns,
    )
    if drift.has_breaking_drift:
        raise ValueError(f"Breaking schema drift in MCA JSON: missing {drift.missing_columns}")

    raw_rows = len(df)
    parsed_rows: list[dict[str, Any]] = []
    invalid_cin_count = 0

    for _, row in df.iterrows():
        cin_raw = normalise_text(row.get("CIN"))
        if not cin_raw:
            invalid_cin_count += 1
            continue
        try:
            parsed = parse_cin(cin_raw)
        except ValueError:
            invalid_cin_count += 1
            continue

        addr = normalise_text(row.get("Registered_Office_Address"))
        state_name = normalise_state(row.get("CompanyStateCode"), iso_hint=parsed.state_code)

        def to_float(v: Any) -> float | None:
            s = normalise_text(v)
            if not s:
                return None
            try:
                return float(s)
            except ValueError:
                return None

        parsed_rows.append({
            "cin": parsed.cin,
            "company_name": normalise_text(row.get("CompanyName")),
            "company_status": normalise_status(row.get("CompanyStatus")),
            "listing_status": normalise_text(row.get("Listingstatus")) or ("Listed" if parsed.listing_status == "L" else "Unlisted"),
            "cin_listing_flag": parsed.listing_status,
            "industry_code": parsed.industry_code,
            "cin_state_code": parsed.state_code,
            "incorporation_year": parsed.incorporation_year,
            "ownership_type": parsed.ownership_type,
            "registration_number": parsed.registration_number,
            "roc_code": normalise_text(row.get("CompanyROCcode")),
            "company_category": normalise_text(row.get("CompanyCategory")),
            "company_class": normalise_text(row.get("CompanyClass")),
            "industrial_classification": normalise_text(row.get("CompanyIndustrialClassification")),
            "authorized_capital": to_float(row.get("AuthorizedCapital")),
            "paidup_capital": to_float(row.get("PaidupCapital")),
            "registration_date": normalise_text(row.get("CompanyRegistrationdate_date")),
            "registered_address": addr,
            "state_name": state_name,
            "pincode": extract_pincode(addr),
            "source": "mca_company_datagovin",
            "ingested_at": meta_latest.get("fetched_at", datetime.now(timezone.utc).isoformat()),
            "source_version": str(meta_latest.get("source_version", "unknown")),
        })

    out_df = pd.DataFrame(parsed_rows)
    dup_count = int(out_df.duplicated(subset=["cin"]).sum())
    out_df = out_df.drop_duplicates(subset=["cin"], keep="first").reset_index(drop=True)

    metrics = {
        "source": "mca_company",
        "raw_rows": raw_rows,
        "clean_rows": len(out_df),
        "invalid_cin_dropped": invalid_cin_count,
        "duplicates_dropped": dup_count,
        "null_rate_pincode": round(float(out_df["pincode"].isna().mean()), 4),
        "null_rate_state_name": round(float(out_df["state_name"].isna().mean()), 4),
    }
    return out_df, metrics


def transform_gst_hsn_sac(raw_dir: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Clean and unify CBIC-derived HSN and SAC tariff codes."""
    hsn_path = raw_dir / "hsn.csv"
    sac_path = raw_dir / "sac.csv"
    meta = json.loads((raw_dir / "hsn.csv.meta.json").read_text(encoding="utf-8"))

    hsn_df = pd.read_csv(hsn_path, dtype=str)
    sac_df = pd.read_csv(sac_path, dtype=str)

    hsn_clean = pd.DataFrame({
        "tariff_code": hsn_df["code"].astype(str).str.strip().str.zfill(4),
        "code_type": "HSN",
        "description": hsn_df["description"].apply(normalise_text),
        "chapter_or_group": hsn_df["chapter"].apply(normalise_text),
    })
    sac_clean = pd.DataFrame({
        "tariff_code": sac_df["code"].astype(str).str.strip(),
        "code_type": "SAC",
        "description": sac_df["description"].apply(normalise_text),
        "chapter_or_group": sac_df.get("category", pd.Series([None] * len(sac_df))).apply(normalise_text),
    })

    combined = pd.concat([hsn_clean, sac_clean], ignore_index=True)
    raw_rows = len(combined)
    dup_count = int(combined.duplicated(subset=["code_type", "tariff_code"]).sum())
    combined = combined.drop_duplicates(subset=["code_type", "tariff_code"], keep="first").reset_index(drop=True)
    combined["source"] = "cbic_hsn_sac_mirror"
    combined["ingested_at"] = meta["fetched_at"]
    combined["source_version"] = meta["source_version"]

    metrics = {
        "source": "gst_hsn_sac",
        "raw_rows": raw_rows,
        "clean_rows": len(combined),
        "duplicates_dropped": dup_count,
        "null_rate_description": round(float(combined["description"].isna().mean()), 4),
    }
    return combined, metrics


def build_validated_gstin_fixture_df() -> pd.DataFrame:
    """Validate synthetic/reference GSTINs using mod-36 checksum & structural parser.

    Note: Live per-GSTIN lookup on services.gst.gov.in is captcha-gated and not scraped.
    This table demonstrates GSTIN structural parsing & checksum validation linked to dim_state.
    """
    from src.validate.validators import compute_gstin_checksum

    # Construct valid-checksum reference GSTINs aligned with states in our MCA/IFSC data
    prefixes = [
        ("24AABCE1234F1Z", "EMSGLOB TECHNOLOGIES PRIVATE LIMITED (TEST FIXTURE)", "ACTIVE"),
        ("27AAACS1234A1Z", "SAMPLE MAHARASHTRA ENTITY (TEST FIXTURE)", "ACTIVE"),
        ("07AAACZ9999B1Z", "SAMPLE DELHI ENTITY (TEST FIXTURE)", "CANCELLED"),
        ("29AABCK5678C1Z", "SAMPLE KARNATAKA ENTITY (TEST FIXTURE)", "ACTIVE"),
    ]
    now_iso = datetime.now(timezone.utc).isoformat()
    rows = []
    for p14, trade_name, status in prefixes:
        gstin = p14 + compute_gstin_checksum(p14)
        parsed = parse_gstin(gstin)
        rows.append({
            "gstin": parsed.gstin,
            "gst_state_code": parsed.state_code,
            "pan_segment": parsed.pan_segment,
            "entity_number": parsed.entity_number,
            "checksum_char": parsed.checksum_char,
            "checksum_valid": parsed.checksum_valid,
            "legal_name": trade_name,
            "registration_status": status,
            "source": "gstin_validator_fixture",
            "ingested_at": now_iso,
            "source_version": "fixture-v1",
        })
    return pd.DataFrame(rows)


def transform_gleif_lei(raw_dir: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Clean and standardise Indian LEI records from official GLEIF API JSON."""
    records: list[dict[str, Any]] = []
    meta_latest: dict[str, Any] = {}
    for page_file in sorted(raw_dir.glob("gleif_in_page_*.json")):
        payload = json.loads(page_file.read_text(encoding="utf-8"))
        meta_file = raw_dir / f"{page_file.name}.meta.json"
        if meta_file.exists():
            meta_latest = json.loads(meta_file.read_text(encoding="utf-8"))
        records.extend(payload.get("data", []))

    if not records:
        raise ValueError(f"No GLEIF records found in {raw_dir}")

    rows: list[dict[str, Any]] = []
    for rec in records:
        attrs = rec.get("attributes", {})
        ent = attrs.get("entity", {})
        addr = ent.get("legalAddress") or {}
        reg_at = ent.get("registeredAt") or {}
        pin_raw = normalise_text(addr.get("postalCode"))
        pin = extract_pincode(pin_raw) if pin_raw else None
        reg_as = normalise_text(ent.get("registeredAs"))
        rows.append({
            "lei": str(rec["id"]).strip().upper(),
            "legal_name": normalise_text((ent.get("legalName") or {}).get("name")),
            "entity_status": normalise_status(ent.get("status")),
            "registration_authority_id": normalise_text(reg_at.get("id")),
            "registered_as": reg_as.upper() if reg_as else None,
            "city": normalise_text(addr.get("city")),
            "country": normalise_text(addr.get("country")),
            "pincode": pin,
            "source": "gleif_lei_official",
            "ingested_at": meta_latest.get("fetched_at", datetime.now(timezone.utc).isoformat()),
            "source_version": str(meta_latest.get("source_version", "gleif-v1")),
        })

    df = pd.DataFrame(rows)
    raw_rows = len(df)
    dup_count = int(df.duplicated(subset=["lei"]).sum())
    df = df.drop_duplicates(subset=["lei"], keep="first").reset_index(drop=True)
    metrics = {
        "source": "gleif_lei",
        "raw_rows": raw_rows,
        "clean_rows": len(df),
        "duplicates_dropped": dup_count,
        "null_rate_registered_as": round(float(df["registered_as"].isna().mean()), 4),
        "null_rate_pincode": round(float(df["pincode"].isna().mean()), 4),
    }
    return df, metrics
