-- Query 1: Cross-source join (MCA Companies + RBI Bank Branches + State Master) by gst_state_code & pincode
SELECT
    s.gst_state_code,
    s.state_name,
    COUNT(DISTINCT c.cin) AS mca_companies,
    COUNT(DISTINCT b.ifsc) AS total_bank_branches,
    COUNT(DISTINCT CASE WHEN b.pincode = c.pincode AND c.pincode IS NOT NULL THEN b.ifsc END) AS branches_in_company_pincode
FROM warehouse.dim_state s
LEFT JOIN warehouse.dim_company c
    ON s.gst_state_code = c.gst_state_code AND c.is_current = TRUE
LEFT JOIN warehouse.dim_bank_branch b
    ON s.gst_state_code = b.gst_state_code
GROUP BY s.gst_state_code, s.state_name
HAVING COUNT(DISTINCT c.cin) > 0
ORDER BY mca_companies DESC, total_bank_branches DESC;

-- Query 2: Company-level banking density enrichment (CIN + Pincode -> Nearby UPI/RTGS-enabled branches)
SELECT
    c.cin,
    c.company_name,
    c.company_status,
    c.incorporation_year,
    c.ownership_type,
    c.state_name,
    c.pincode,
    COUNT(b.ifsc) AS branches_in_same_pincode,
    SUM(CASE WHEN b.upi THEN 1 ELSE 0 END) AS upi_enabled_branches
FROM warehouse.dim_company c
LEFT JOIN warehouse.dim_bank_branch b
    ON c.pincode = b.pincode
WHERE c.is_current = TRUE
GROUP BY
    c.cin, c.company_name, c.company_status, c.incorporation_year,
    c.ownership_type, c.state_name, c.pincode
ORDER BY branches_in_same_pincode DESC, c.cin
LIMIT 10;

-- Query 3: Cross-source State + GSTIN + MCA + Branch summary
SELECT
    s.gst_state_code,
    s.state_name,
    COUNT(DISTINCT g.gstin) AS validated_gstins,
    COUNT(DISTINCT c.cin) AS mca_companies,
    COUNT(DISTINCT b.ifsc) AS bank_branches
FROM warehouse.dim_state s
LEFT JOIN warehouse.fact_gst_registration g
    ON s.gst_state_code = g.gst_state_code
LEFT JOIN warehouse.dim_company c
    ON s.gst_state_code = c.gst_state_code AND c.is_current = TRUE
LEFT JOIN warehouse.dim_bank_branch b
    ON s.gst_state_code = b.gst_state_code
GROUP BY s.gst_state_code, s.state_name
HAVING COUNT(DISTINCT g.gstin) > 0 OR COUNT(DISTINCT c.cin) > 0
ORDER BY validated_gstins DESC, mca_companies DESC;
