"""Build CATALOG_INVENTORY.csv from live Surepass.io and Perfios.ai sitemaps."""

from __future__ import annotations

import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

import httpx

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def classify_url(vendor: str, url: str) -> tuple[str, str, str, str, str, str]:
    """Return (category, inputs, outputs, likely_upstream, classification, reason)."""
    slug = urlparse(url).path.strip("/").split("/")[-1].lower()

    # Personal data / Individual KYC
    if any(k in slug for k in ["aadhaar", "okyc", "vcip", "video-kyc", "face-", "liveness", "deepfake", "voter", "passport", "driving", "drivers-license", "dl-", "ration", "abha", "eshram", "e-shram", "apaar", "umid", "oci", "death-certificate", "10th-marksheet", "12th-marksheet", "marksheet", "age-verification", "emirates-id", "bangladesh-national-id", "emirati-passport"]):
        return (
            "Identity / Individual KYC",
            "ID number / Document image / OTP / Biometric",
            "Individual PII, DOB, address, photo, verification status",
            "UIDAI / ECI / MEA / Parivahan / State Registrars",
            "personal data",
            "Eliminated: personal data of private individuals (DPDP Act 2023 & assignment exclusion).",
        )

    # Consent-gated / Financial / Tax / Employment
    if any(k in slug for k in ["account-aggregator", "perfios-aa", "fip", "fiu", "consent-management", "bank-statement", "itr", "ais-", "payslip", "epfo", "uan", "employment-history", "dual-employment", "penny-drop", "bank-account", "upi", "money-mule", "wealth-profiling", "cam", "crilc", "uli", "credit-gateway", "ckyc"]):
        return (
            "Financial / Income / Employment",
            "Account number / Consent handle / UAN / ITR credentials / Bank PDF",
            "Account balances, transactions, income, employment history, credit profile",
            "RBI Account Aggregator / NPCI / EPFO / Income Tax Dept / CERSAI / Credit Bureaus",
            "consent-gated",
            "Eliminated: consent-gated or proprietary financial/credit/employment data.",
        )

    # Proprietary / Telecom / Vehicle / Utility / Fraud / Platform
    if any(k in slug for k in ["vehicle", "rc-", "challan", "stolen-vehicle", "telecom", "mnrl", "mobile-number", "digital-footprint", "email-id-verification", "tamper", "fraud", "hyperpersonalization", "journey-builder", "onesdk", "onevigil", "oneview", "oneclick", "trustarmour", "garner", "iadore", "acclaim", "integreat", "leadgen", "kscan", "perfios-hub", "perfios-switch", "dpi-stack", "e-stamping", "esign", "e-sign", "digital-signature", "fnr-tracking", "pre-issuance"]):
        return (
            "Proprietary / Telecom / Vehicle / Platform",
            "Vehicle RC / Phone / Email / Document / SDK session",
            "Risk score, RC owner details, telecom status, or SaaS workflow",
            "MoRTH Vahan / Telcos / Proprietary ML models",
            "proprietary",
            "Eliminated: proprietary scoring/SaaS or restricted/personal Vahan/telecom data.",
        )

    # Entity-level public data candidates!
    if "ifsc" in slug:
        return (
            "Banking Infrastructure (Entity/Branch)",
            "11-char IFSC code",
            "Bank name, branch name, address, city, state, MICR, NEFT/RTGS/IMPS/UPI flags",
            "Reserve Bank of India (RBI) NEFT/RTGS Directory",
            "entity-level public data",
            "SURVIVOR: Public RBI branch master; open MIT mirror (razorpay/ifsc) + zero PII.",
        )
    if any(k in slug for k in ["mca", "cin", "din", "company", "struck-off", "signatory", "lei-validation", "corporate", "due-diligence", "legal-search", "litigation", "pep-screening", "compliance-check"]):
        return (
            "Corporate Registry / KYB",
            "CIN / LLPIN / Company Name / LEI",
            "Company master, status, RoC, incorporation date, capital, registered address",
            "Ministry of Corporate Affairs (MCA) / GLEIF / Courts / Sanctions lists",
            "entity-level public data",
            "SURVIVOR: Entity-level corporate registry; MCA master available via data.gov.in (GODL).",
        )
    if any(k in slug for k in ["gst", "hsn", "sac"]):
        return (
            "Tax & Trade Classification (Entity)",
            "15-char GSTIN / HSN / SAC code",
            "Legal name, trade name, state code, registration status, HSN/SAC tariff descriptions",
            "GSTN (services.gst.gov.in) / CBIC (cbic-gst.gov.in)",
            "entity-level public data",
            "SURVIVOR: Entity-level tax & HSN/SAC classification; live GSTN lookup captcha-gated, CBIC HSN/SAC open.",
        )
    if any(k in slug for k in ["udyam", "msme", "fssai", "iec", "shop-and-establishment", "rera", "digipin"]):
        return (
            "Business Licenses & Geo-Codes (Entity)",
            "Udyam No / FSSAI License / IEC / RERA ID / Coordinates",
            "Business registration status, entity name, address, license validity",
            "Ministry of MSME / FSSAI / DGFT / State RERA / Dept of Posts",
            "entity-level public data",
            "SURVIVOR (Secondary): Entity-level business license; fragmented or OTP/captcha-gated portals.",
        )

    # Generic OCR / Address / Document tools
    return (
        "Document / Utility / Other",
        "Document image / raw text",
        "Extracted fields / parsed address / generic verification",
        "Internal OCR / NLP / Mixed",
        "proprietary",
        "Eliminated: generic utility/OCR wrapper without a standalone public entity dataset.",
    )


def build_inventory(out_path: Path) -> None:
    rows: list[dict[str, str]] = []
    with httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "ZintrlDataEngineeringTakeHome/1.0"}) as c:
        sp = c.get("https://surepass.io/page-sitemap.xml")
        sp_urls = [el.text for el in ET.fromstring(sp.content).findall(".//sm:loc", NS) if el.text]

        pf = c.get("https://perfios.ai/page-sitemap.xml")
        pf_urls = [el.text for el in ET.fromstring(pf.content).findall(".//sm:loc", NS) if el.text]

    # Filter to API/product pages
    sp_api_urls = [
        u for u in sp_urls
        if any(k in u.lower() for k in ["api", "verification", "kyc", "kyb", "mca", "gst", "ifsc", "pan", "aadhaar", "bank", "epfo", "udyam", "msme", "vehicle", "rc", "fssai", "lei", "ckyc", "din", "cin", "ocr", "esign", "digipin", "hsn", "iec", "rera"])
    ]
    pf_prod_urls = [
        u for u in pf_urls
        if ("/products/" in u or "/in/" in u or any(k in u.lower() for k in ["kyc", "analyzer", "analyser", "perfios-aa", "sourcing", "monitoring", "legal-search"]))
        and not u.rstrip("/").endswith("/products")
    ]

    for vendor, urls, auth, sandbox in [
        ("Surepass.io", sp_api_urls, "Bearer API Key (commercial)", "Sandbox available on signup"),
        ("Perfios (perfios.ai / Hub)", pf_prod_urls, "OAuth2 / API Key via Perfios Hub (enterprise)", "Sandbox credits on Perfios Hub"),
    ]:
        for u in urls:
            slug = urlparse(u).path.strip("/").split("/")[-1]
            name = slug.replace("-", " ").title()
            cat, inp, outp, upstream, cls, reason = classify_url(vendor, u)
            rows.append({
                "vendor": vendor,
                "api_name": name,
                "catalog_url": u,
                "category": cat,
                "inputs": inp,
                "outputs": outp,
                "auth_model": auth,
                "pricing_or_sandbox": sandbox,
                "likely_upstream_source": upstream,
                "classification": cls,
                "elimination_or_selection_reason": reason,
            })

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    from collections import Counter
    counts = Counter(r["classification"] for r in rows)
    print(f"Wrote {len(rows)} rows to {out_path}. Breakdown: {dict(counts)}")


if __name__ == "__main__":
    build_inventory(Path("CATALOG_INVENTORY.csv"))
