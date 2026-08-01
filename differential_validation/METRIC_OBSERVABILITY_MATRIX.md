# Metric observability matrix

| Metric | Comparator | Source | Status | Value | Reason |
|---|---|---|---|---|---|
| COMPONENT_PRESENCE_MISMATCH | yes | yes | MEASURED | 0 | Compared for every applicable response row |
| COMPONENT_TYPE_MISMATCH | yes | yes | MEASURED | 0 | Compared for every applicable response row |
| ROUNDED_AMOUNT_MISMATCH | yes | yes | MEASURED | 0 | Compared for every applicable response row |
| TAXABLE_BASE_MISMATCH | yes | yes | MEASURED | 0 | Compared for every applicable response row |
| GROSS_MISMATCH | yes | yes | MEASURED | 0 | Compared for every applicable response row |
| DEDUCTION_MISMATCH | yes | yes | MEASURED | 0 | Compared for every applicable response row |
| TAX_MISMATCH | yes | yes | MEASURED | 0 | Compared for every applicable response row |
| NET_MISMATCH | yes | yes | MEASURED | 0 | Compared for every applicable response row |
| SOURCE_RULE_ID_MISMATCH | yes | yes | MEASURED | 0 | Compared for every applicable response row |
| RULE_VERSION_ID_MISMATCH | yes | yes | MEASURED | 0 | Compared for every applicable response row |
| CONTRIBUTOR_IDS_MISMATCH | yes | yes | MEASURED | 0 | Compared for every applicable response row |
| RUNTIME_ERROR | yes | yes | MEASURED | 0 | Compared for every applicable response row |
| TIMEOUT | yes | yes | MEASURED | 0 | Compared for every applicable response row |
| RAW_AMOUNT_MISMATCH | no | no | NOT_OBSERVABLE | null | Production API does not expose the pre-rounding candidate amount |
| ROUNDING_POINT_MISMATCH | no | no | NOT_OBSERVABLE | null | Production API does not expose the exact rounding decision point |
| RATE_VERSION_MISMATCH | no | no | NOT_OBSERVABLE | null | Production response does not identify the resolved payroll-rate version |
| TAX_VERSION_MISMATCH | no | no | NOT_OBSERVABLE | null | Production response does not identify the resolved company-tax version |
| TRANSLATION_MISMATCH | no | no | NOT_APPLICABLE | null | Measured in the separate translator fixture validation, not this runtime run |

A numeric zero appears only for measured metrics. Unobservable and non-applicable metrics carry a null value.
