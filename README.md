# Zintrl Data Engineering Take-Home: Public Entity Data Sourcing & Warehouse

Compliance-first, end-to-end data sourcing and warehousing pipeline built on **public, free, and legitimately accessible** Indian entity-level datasets:
1. **RBI IFSC / Bank Branch Master** (`razorpay/ifsc` `v2.0.62`, MIT License — **183,214** branches)
2. **MCA Company Master Data** (`api.data.gov.in` Resource `4dbe5667-7b6b-41d7-82af-211562424d9a`, GODL License)
3. **GST HSN/SAC Master & GSTIN Mod-36 Validator** (CBIC MIT/Apache-2.0 mirrors + structural/checksum parser)

## Deliverables
- [`APPROACH.md`](file:///Users/parthsingh/Documents/data-mine/APPROACH.md) — Final submission report, architecture diagram, metrics, risks, and land-records comparison
- [`SOURCE_DECISION_LOG.md`](file:///Users/parthsingh/Documents/data-mine/SOURCE_DECISION_LOG.md) — Detailed discovery, upstream tracing, `robots.txt` / license audits, and mode decisions
- [`CATALOG_INVENTORY.csv`](file:///Users/parthsingh/Documents/data-mine/CATALOG_INVENTORY.csv) — 612 Surepass.io & Perfios APIs classified and filtered to entity-level public data
- [`docs/sample_query_outputs.txt`](file:///Users/parthsingh/Documents/data-mine/docs/sample_query_outputs.txt) — Captured cross-source DuckDB SQL query outputs

## Quickstart

```bash
# 1. Create virtual environment and install dependencies
python3 -m venv .venv
.venv/bin/pip install -e . pytest

# 2. Run live ingestion (respects robots.txt, rate limits, and writes SHA-256 .meta.json)
.venv/bin/python -m src.ingest.ifsc_ingest
export DATA_GOV_IN_API_KEY="your_free_datagovin_key"  # optional; defaults to public sample key
.venv/bin/python -m src.ingest.mca_ingest
.venv/bin/python -m src.ingest.gst_ingest

# 3. Clean, validate, and load DuckDB warehouse (idempotent SCD Type 2)
.venv/bin/python -m warehouse.load_warehouse

# 4. Run unit & warehouse idempotency tests
.venv/bin/pytest -v
```
