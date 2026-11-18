# Source Decision Log

**Access Date:** `2026-11-18`  
**Posture:** Compliance-first. Only public, free, and legitimately accessible entity-level sources are ingested. Every claim below is labeled `verified` (directly observed in HTTP responses, downloaded files, or tool output), `inferred` (logically deduced from observed evidence), or `undetermined` (behind login/sandbox or unverified).

---

## 1. Source 1: IFSC / Bank Branch Master (`rbi_ifsc_razorpay`)

### Catalog Analysis (Live Retrieved Vendor Pages)
- **Surepass.io (`https://surepass.io/ifsc-code-verification-api/`):** Retrieved HTTP `200` on `2026-11-18` (`verified`). Title: *"IFSC Code Verification API for Bank Details – Surepass"*. Input: 11-char IFSC code; Output: bank name, branch, address, MICR, NEFT/RTGS/IMPS/UPI flags. Auth: Bearer API Key obtained via free sandbox account signup (*"Get API Key / By creating a free account, you get..."*).
- **Perfios (`https://perfios.ai/in/products/kyc-kyb/`):** Retrieved HTTP `200` on `2026-11-18` (`verified`). Title: *"Business KYC & KYB Verification Solutions | Perfios"*. Bundles entity IDs, banking/IFSC, and KYB verification behind enterprise OAuth2/API Key on `hub.perfios.com` (`undetermined` exact JSON schema without enterprise login).

### Upstream Tracing & Mirror vs. Authority Distinction
- **Authoritative Upstream:** Reserve Bank of India (RBI) NEFT/RTGS bank branch directory (`verified`). RBI publishes periodic Excel workbooks on `rbi.org.in`, which are non-uniformly formatted across updates.
- **Open-Source Mirror Used:** `razorpay/ifsc` on GitHub (`https://github.com/razorpay/ifsc/releases`), latest release **`v2.0.62`** published `2026-09-01T11:55:03Z` (`verified`).
  - **Mirror vs. Authority Note:** `razorpay/ifsc` is a **third-party MIT-licensed mirror**, not the primary regulator (`RBI`). For this prototype, we use Razorpay's release because it parses RBI's Excel sheets into clean, schema-stable CSV/JSON with zero scraping fragility. In production at Zintrl, we would either ingest RBI's primary NEFT/RTGS files directly (using Razorpay's open-source parser logic) or cross-verify deltas against `rbi.org.in` so we never depend solely on a third-party mirror's release cadence.
  - Assets observed (`verified`): `IFSC.csv` (36,368,257 bytes), `banks.json` (299,463 bytes), `IFSC-list.json`, `IFSC.json`, `by-bank.tar.gz`, `sublet.json`.
  - Live public REST endpoint tested: `https://ifsc.razorpay.com/SBIN0000001` returned HTTP `200` with JSON (`verified`).

### Legitimacy Audit
- **License:** MIT License (`razorpay/ifsc` mirror) derived from public RBI directory (`verified`). Permits commercial aggregation and redistribution.
- **`robots.txt`:** Checked via `src/ingest/robots_checker.py` against `api.github.com` before fetch -> `allowed: True` (`verified`).
- **DPDP Act 2023:** Zero personal data; purely institutional bank branch metadata (`verified`).

### Mode Decision
- **Chosen:** Bulk release download (`IFSC.csv` + `banks.json`) from GitHub Releases (`v2.0.62`), falling back to `ifsc.razorpay.com/<IFSC>` for point lookups (`verified`).
- **Rejected:** Commercial Surepass/Perfios API (unnecessary cost for static public master), scraping RBI Excel/HTML tables directly (fragile formatting).

### Per-Source Record
| Field | Value |
|---|---|
| **URL** | `https://api.github.com/repos/razorpay/ifsc/releases/latest` |
| **Owner** | RBI (upstream) / Razorpay (MIT mirror) |
| **License** | MIT License |
| **Auth Type** | None (public GitHub release) |
| **Refresh Cadence** | Monthly / aligned with RBI updates (`v2.0.62` = `2026-09-01`) |
| **Format & Size** | CSV (`36.37 MB`) + JSON (`299 KB`) |
| **Access Date** | `2026-11-18` |
| **Known Limitations** | `BANK` column is `NaN` on ~0.56% of rows even after `banks.json` enrichment; 38.07% of addresses lack a 6-digit pincode (`verified`). |

---

## 2. Source 2: MCA Company Master Data (`mca_company_datagovin`)

### Catalog Analysis
- **Surepass.io:** MCA Data APIs (V3 Portal / CIN & DIN), Struck Off Companies Check, Corporate Signatory Details (`verified` in `surepass.io` sitemap).
- **Perfios (Karza):** Corporate registry / KYB & Due Diligence (`https://perfios.ai/in/products/kyc-kyb/`, `https://perfios.ai/in/products/due-diligence/`, `verified` in `perfios.ai` sitemap).

### Upstream Tracing & Open-Source Search
- **Authoritative Upstream:** Ministry of Corporate Affairs (MCA), Government of India (`verified`).
- **`data.gov.in` Official API:** Resource ID `4dbe5667-7b6b-41d7-82af-211562424d9a` (*"Registrars of Companies (RoC)-wise Company Master Data"*, `org: ["Ministry of Corporate Affairs"]`) (`verified` via live HTTP 200 response).
  - Total records reported by API: **`3,738,721`** (`verified`).
- **Rejected Open-Source Mirrors:**
  - `matcdac/CorporateIndiaDataSourceXLSX` on GitHub: inspected via GitHub API -> `license: None`, data from `2015–2016` (`2015.7z.001..008`, `2016.7z.001..006`) (`verified`). Rejected due to missing license and 10-year staleness.

### Legitimacy Audit
- **License:** Government Open Data License - India (GODL) (`verified` for `data.gov.in` datasets). Permits commercial reuse with attribution.
- **`robots.txt`:**
  - `https://www.data.gov.in/robots.txt` returned `User-agent: * \n Disallow: /` (`verified`) -> **Do NOT scrape the web portal.**
  - `https://api.data.gov.in/robots.txt` returned HTTP `404` (`verified`) -> Official API is open for programmatic access with an API key.
  - `https://www.mca.gov.in/robots.txt` returned HTTP `403 Access Denied` (Akamai EdgeSuite WAF) (`verified`) -> Do NOT scrape `mca.gov.in`.
- **DPDP Act 2023:** Company Master Data contains entity-level corporate attributes (CIN, Company Name, Status, Capital, Registered Office Address). Director PII (DIN/PAN) is excluded (`verified`).

### Mode Decision
- **Chosen:** Official `api.data.gov.in` REST API (`src/ingest/mca_ingest.py`), supporting `DATA_GOV_IN_API_KEY` env var and defaulting to the documented public sample key for bounded demonstration (`verified`).
- **Rejected:** Direct scraping of `mca.gov.in` (403 WAF) or `www.data.gov.in` (`Disallow: /`), unlicensed GitHub 2015 dumps.

### Per-Source Record
| Field | Value |
|---|---|
| **URL** | `https://api.data.gov.in/resource/4dbe5667-7b6b-41d7-82af-211562424d9a` |
| **Owner** | Ministry of Corporate Affairs (via `data.gov.in`) |
| **License** | Government Open Data License - India (GODL) |
| **Auth Type** | Free personal API key (`data.gov.in` account, passed via `DATA_GOV_IN_API_KEY`); sample key capped at 10 rows/req & strict 429 rate limits (`verified`) |
| **Refresh Cadence** | Periodic RoC-wise snapshots |
| **Format & Size** | JSON (`3,738,721` total records in API; `2,000` unique records loaded across 4 pages of 500 via personal API key) |
| **Access Date** | `2026-11-18` |
| **Known Limitations** | Sample key hits HTTP `429 Rate limit exceeded` after ~3 pages (`offset=30`); `nic_code` field is often `"NA"` even when 5-digit NIC code is embedded in `CIN[1:6]` (`verified`). |

---

## 3. Source 3: Legal Entity Identifier (LEI) — Official GLEIF (`gleif_lei_official`)

### Catalog Analysis (Live Retrieved Vendor Pages)
- **Surepass.io (`https://surepass.io/lei-validation-api/`):** Retrieved HTTP `200` on `2026-11-18` (`verified`). Title: *"LEI Validation API - Surepass"*. Description: *"The LEI Validation API helps in the instant verification of LEI codes and company information accurately."* Input: 20-character LEI code; Output: entity legal name, status, registration authority, address. Auth: Bearer API Key (`Get API Key` free sandbox signup).
- **Perfios:** Covered under `kyc-kyb` / `due-diligence` corporate entity verification (`https://perfios.ai/in/products/kyc-kyb/`, `verified`).

### Upstream Tracing & Open-Source Search
- **Authoritative Upstream:** Global Legal Entity Identifier Foundation (**GLEIF**), `https://api.gleif.org/api/v1/lei-records` (`verified`). Unlike IFSC (where we used an MIT mirror), this is the **direct authoritative global registry**, free, unauthenticated, and updated 3x daily.
- **Live Probe (`2026-11-18`):** `https://api.gleif.org/api/v1/lei-records?filter[entity.legalAddress.country]=IN` returned HTTP `200` with **`411,277`** Indian corporate entities (`verified`).
- **Entity Richness:** Records include `lei`, `legalName`, `status`, `legalAddress.postalCode`, `registeredAt.id` (e.g., `RA000394` = MCA India), and `registeredAs` — which directly surfaces **MCA CINs/LLPINs**, **public GSTINs**, and **Udyam MSME IDs** (`verified`).

### Legitimacy Audit
- **License:** **CC0 1.0 Universal (Public Domain)** (`verified`). Commercial aggregation and redistribution are explicitly permitted without restriction.
- **`robots.txt`:** `https://api.gleif.org/robots.txt` returned HTTP `200` with `User-agent: * \n Disallow:` (`verified`).
- **DPDP Act 2023:** Purely corporate/institutional entity data (`verified`).

### Per-Source Record
| Field | Value |
|---|---|
| **URL** | `https://api.gleif.org/api/v1/lei-records?filter[entity.legalAddress.country]=IN` |
| **Owner** | Global Legal Entity Identifier Foundation (GLEIF) |
| **License** | CC0 1.0 Universal (Public Domain) |
| **Auth Type** | None (open REST API) |
| **Refresh Cadence** | Daily (GLEIF publishes 3x daily) |
| **Format & Size** | JSON:API (`411,277` Indian entities; `200` landed across 2 pages in demo) |
| **Access Date** | `2026-11-18` |
| **Known Limitations** | Covers entities that have obtained an LEI (typically larger corporates, exporters, borrowers); `1.0%` of sampled records had null `registered_as` (`verified`). |

---

## 4. Source 4 (Supplemental + Production Gap Analysis): GSTIN & HSN/SAC (`gst_masters` + `gstin_validator`)

### Catalog Analysis (Live Retrieved Vendor Pages)
- **Surepass.io (`https://surepass.io/gst-verification-api/`):** Retrieved HTTP `200` on `2026-11-18` (`verified`). Title: *"GST Verification API for Business Validation | Surepass"*. Input: 15-char GSTIN; Output: legal name, trade name, registration status, principal place of business. Auth: Bearer API Key (sandbox signup).
- **Perfios (`https://perfios.ai/products/gst-analyser/`):** Listed in `perfios.ai` sitemap (`verified`); return-level analytics require taxpayer consent/OTP.

### Upstream Tracing & Open-Source Search
- **Authoritative Upstream:** Goods and Services Tax Network (GSTN) (`services.gst.gov.in`) and Central Board of Indirect Taxes and Customs (CBIC) (`cbic-gst.gov.in`) (`verified`).
- **Open-Source CBIC HSN/SAC Mirrors:**
  - `zee4refer/hsn-sac-codes-india` (MIT License): `hsn.csv` (83,340 bytes), `sac.csv` (32,662 bytes) (`verified`).
  - `frontlook-admin/HSN-Code-Classifier` (Apache-2.0 License): `HSNChapters.json` (44,978 bytes) (`verified`).

### Legitimacy Audit
- **`robots.txt` & Captcha Gating:**
  - `https://services.gst.gov.in/robots.txt` and `https://www.gst.gov.in/robots.txt` return HTTP `404` HTML error page (`verified`).
  - Live per-GSTIN taxpayer lookup (`https://services.gst.gov.in/services/searchtp`) is **captcha-gated** (`verified` via GSTN portal design). Per hard constraints, we **never** bypass captchas.
  - Therefore: we ingest **real public CBIC HSN/SAC master tables** (MIT/Apache-2.0) and implement **GSTIN 15-character structural + mod-36 checksum validation** on reference fixtures, documenting that live per-GSTIN enrichment requires a licensed **GSP (GST Suvidha Provider)** API or commercial vendor sandbox (`verified`).

### Mode Decision
- **Chosen:** Public MIT/Apache-2.0 CBIC HSN/SAC bulk files + deterministic GSTIN structural/checksum parser + `dim_state` (36 GST state codes `01`–`38`).
- **Rejected:** Automated scraping of `services.gst.gov.in/services/searchtp` (captcha-gated).

### Per-Source Record
| Field | Value |
|---|---|
| **URL** | `https://github.com/zee4refer/hsn-sac-codes-india` & `https://github.com/frontlook-admin/HSN-Code-Classifier` |
| **Owner** | CBIC / GSTN (upstream); `zee4refer` (MIT) & `frontlook-admin` (Apache-2.0) |
| **License** | MIT / Apache-2.0 |
| **Auth Type** | None for HSN/SAC bulk; GSP/Vendor key required for live GSTIN taxpayer status |
| **Refresh Cadence** | Tariff-schedule updates (CBIC) |
| **Format & Size** | CSV + JSON (`~160 KB` total, `649` unified HSN/SAC rows) |
| **Access Date** | `2026-11-18` |
| **Known Limitations** | Live per-GSTIN taxpayer status & PAN-to-GSTIN mapping cannot be sourced freely without a GSP license or captcha (`verified`). |
