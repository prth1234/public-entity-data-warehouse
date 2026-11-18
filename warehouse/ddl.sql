CREATE SCHEMA IF NOT EXISTS raw_staging;
CREATE SCHEMA IF NOT EXISTS warehouse;

CREATE TABLE IF NOT EXISTS warehouse.dim_state (
    gst_state_code VARCHAR PRIMARY KEY,
    iso_state_code VARCHAR NOT NULL,
    state_name VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS warehouse.dim_bank_branch (
    ifsc VARCHAR PRIMARY KEY,
    bank_code VARCHAR NOT NULL,
    bank_name VARCHAR,
    branch_name VARCHAR,
    address VARCHAR,
    city VARCHAR,
    district VARCHAR,
    state_name VARCHAR,
    gst_state_code VARCHAR,
    pincode VARCHAR,
    micr VARCHAR,
    neft BOOLEAN,
    rtgs BOOLEAN,
    imps BOOLEAN,
    upi BOOLEAN,
    source VARCHAR NOT NULL,
    ingested_at VARCHAR NOT NULL,
    source_version VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS warehouse.dim_company (
    company_sk VARCHAR PRIMARY KEY,
    cin VARCHAR NOT NULL,
    company_name VARCHAR,
    company_status VARCHAR,
    listing_status VARCHAR,
    industry_code VARCHAR,
    cin_state_code VARCHAR,
    incorporation_year INTEGER,
    ownership_type VARCHAR,
    registration_number VARCHAR,
    roc_code VARCHAR,
    company_category VARCHAR,
    company_class VARCHAR,
    industrial_classification VARCHAR,
    authorized_capital DOUBLE,
    paidup_capital DOUBLE,
    registration_date VARCHAR,
    registered_address VARCHAR,
    state_name VARCHAR,
    gst_state_code VARCHAR,
    pincode VARCHAR,
    record_hash VARCHAR NOT NULL,
    valid_from VARCHAR NOT NULL,
    valid_to VARCHAR NOT NULL,
    is_current BOOLEAN NOT NULL,
    source VARCHAR NOT NULL,
    ingested_at VARCHAR NOT NULL,
    source_version VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS warehouse.dim_gstin (
    gstin VARCHAR PRIMARY KEY,
    gst_state_code VARCHAR NOT NULL,
    pan_segment VARCHAR NOT NULL,
    entity_number VARCHAR NOT NULL,
    checksum_char VARCHAR NOT NULL,
    checksum_valid BOOLEAN NOT NULL,
    legal_name VARCHAR,
    registration_status VARCHAR,
    source VARCHAR NOT NULL,
    ingested_at VARCHAR NOT NULL,
    source_version VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS warehouse.dim_hsn_sac (
    code_type VARCHAR NOT NULL,
    tariff_code VARCHAR NOT NULL,
    description VARCHAR,
    chapter_or_group VARCHAR,
    source VARCHAR NOT NULL,
    ingested_at VARCHAR NOT NULL,
    source_version VARCHAR NOT NULL,
    PRIMARY KEY (code_type, tariff_code)
);

CREATE TABLE IF NOT EXISTS warehouse.dim_lei (
    lei VARCHAR PRIMARY KEY,
    legal_name VARCHAR,
    entity_status VARCHAR,
    registration_authority_id VARCHAR,
    registered_as VARCHAR,
    city VARCHAR,
    country VARCHAR,
    pincode VARCHAR,
    source VARCHAR NOT NULL,
    ingested_at VARCHAR NOT NULL,
    source_version VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS warehouse.fact_company_status_snapshot (
    snapshot_date VARCHAR NOT NULL,
    cin VARCHAR NOT NULL,
    gst_state_code VARCHAR,
    company_status VARCHAR,
    authorized_capital DOUBLE,
    paidup_capital DOUBLE,
    source VARCHAR NOT NULL,
    ingested_at VARCHAR NOT NULL,
    source_version VARCHAR NOT NULL,
    PRIMARY KEY (snapshot_date, cin)
);

CREATE TABLE IF NOT EXISTS warehouse.fact_gst_registration (
    gstin VARCHAR NOT NULL,
    gst_state_code VARCHAR NOT NULL,
    pan_segment VARCHAR NOT NULL,
    registration_status VARCHAR NOT NULL,
    checksum_valid BOOLEAN NOT NULL,
    snapshot_date VARCHAR NOT NULL,
    source VARCHAR NOT NULL,
    ingested_at VARCHAR NOT NULL,
    source_version VARCHAR NOT NULL,
    PRIMARY KEY (snapshot_date, gstin)
);
