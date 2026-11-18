SELECT
    ifsc,
    bank_code,
    bank_name,
    branch_name,
    address,
    city,
    district,
    state_name,
    gst_state_code,
    pincode,
    micr,
    neft,
    rtgs,
    imps,
    upi,
    source,
    ingested_at,
    source_version
FROM raw_staging.stg_ifsc
WHERE ifsc IS NOT NULL
