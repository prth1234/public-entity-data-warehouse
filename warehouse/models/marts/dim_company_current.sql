SELECT
    company_sk,
    cin,
    company_name,
    company_status,
    listing_status,
    industry_code,
    cin_state_code,
    incorporation_year,
    ownership_type,
    roc_code,
    authorized_capital,
    paidup_capital,
    registered_address,
    state_name,
    gst_state_code,
    pincode,
    valid_from,
    source,
    ingested_at,
    source_version
FROM warehouse.dim_company
WHERE is_current = TRUE
