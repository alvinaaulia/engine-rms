# Metric observability matrix

| Metric | Status | Value | Denominator | Unit | Reason | Evidence |
|---|---|---|---|---|---|---|
| CASE_EXACT_MATCH | MEASURED | 624 | 624 | case | Calculated from differential comparison rows | runs/fixed/differential_results.csv |
| COMPONENT_EXACT_MATCH | MEASURED | 2592 | 2592 | component comparison | Calculated from differential comparison rows | runs/fixed/differential_results.csv |
| SUMMARY_EXACT_MATCH | MEASURED | 3600 | 3600 | summary comparison | Calculated from differential comparison rows | runs/fixed/differential_results.csv |
| COMPONENT_PRESENCE_MISMATCH | MEASURED | 0 | 2592 | component comparison | Calculated from differential comparison rows | runs/fixed/differential_results.csv |
| COMPONENT_TYPE_MISMATCH | MEASURED | 0 | 2592 | component comparison | Calculated from differential comparison rows | runs/fixed/differential_results.csv |
| ROUNDED_AMOUNT_MISMATCH | MEASURED | 0 | 2592 | component comparison | Calculated from differential comparison rows | runs/fixed/differential_results.csv |
| TAXABLE_BASE_MISMATCH | MEASURED | 0 | 600 | case summary | Calculated from differential comparison rows | runs/fixed/differential_results.csv |
| GROSS_MISMATCH | MEASURED | 0 | 1200 | case summary field | Calculated from differential comparison rows | runs/fixed/differential_results.csv |
| DEDUCTION_MISMATCH | MEASURED | 0 | 600 | case summary | Calculated from differential comparison rows | runs/fixed/differential_results.csv |
| TAX_MISMATCH | MEASURED | 0 | 600 | case summary | Calculated from differential comparison rows | runs/fixed/differential_results.csv |
| NET_MISMATCH | MEASURED | 0 | 600 | case summary | Calculated from differential comparison rows | runs/fixed/differential_results.csv |
| SOURCE_RULE_ID_MISMATCH | MEASURED | 0 | 2592 | component provenance | Calculated from differential comparison rows | runs/fixed/differential_results.csv |
| RULE_VERSION_ID_MISMATCH | MEASURED | 0 | 2592 | component provenance | Calculated from differential comparison rows | runs/fixed/differential_results.csv |
| CONTRIBUTOR_IDS_MISMATCH | MEASURED | 0 | 2592 | component provenance | Calculated from differential comparison rows | runs/fixed/differential_results.csv |
| RUNTIME_ERROR | MEASURED | 0 | 624 | case execution | Calculated from differential comparison rows | runs/fixed/differential_results.csv |
| TIMEOUT | MEASURED | 0 | 624 | case execution | Calculated from differential comparison rows | runs/fixed/differential_results.csv |
| RAW_AMOUNT_MISMATCH | NOT_OBSERVABLE | None | None | component | Production API does not expose the pre-rounding candidate amount | runs/fixed/differential_results.csv |
| ROUNDING_POINT_MISMATCH | NOT_OBSERVABLE | None | None | rounding decision | Production API does not expose the exact rounding decision point | runs/fixed/differential_results.csv |
| RATE_VERSION_MISMATCH | NOT_OBSERVABLE | None | None | rate resolution | Production response does not identify the resolved payroll-rate version | runs/fixed/differential_results.csv |
| TAX_VERSION_MISMATCH | NOT_OBSERVABLE | None | None | tax resolution | Production response does not identify the resolved company-tax version | runs/fixed/differential_results.csv |
| TRANSLATION_MISMATCH | NOT_APPLICABLE | None | None | translator fixture | Measured in the separate translator fixture validation, not this runtime run | translation_validation_fixtures.json |
| PERSISTENCE_RESULT | NOT_APPLICABLE | None | None | E2E transaction | Measured only by the full-pipeline E2E artifact | runs/fixed/full_pipeline_e2e.json |
| TRANSLATOR_FIXTURE_EXACT_MATCH | MEASURED | 12 | 12 | translator fixture | Derived from fixture artifact and dedicated Go JSON test log | runs/hardening/raw-logs/translator-hardening.stdout.log |
| FULL_PAYROLL_PIPELINE_EXACT_MATCH | MEASURED | 32 | 32 | payroll transaction | Expected and actual component snapshot hashes match | e2e-execution-traces.json |
| PERSISTENCE_RESULT | MEASURED | 32 | 32 | persisted payroll transaction | Salary row and relation were asserted in the Laravel E2E test | runs/fixed/full_pipeline_e2e.json |
| GO_REQUEST_ID | NOT_OBSERVABLE | None | None | HTTP request | The current production endpoint does not return a per-request correlation identifier | e2e-execution-traces.json |

Non-measured and unobservable values remain null; zero is used only for measured quantities.
