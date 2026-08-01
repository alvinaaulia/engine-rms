# Oracle Verification and Status Report

## Decision

Status: **FROZEN_REFERENCE_ORACLE / NOT_AUTHORITATIVE_BUSINESS_ORACLE**. The expected results are technically frozen for the experiment; they are not asserted as HRD-authoritative because the cited HRD spreadsheet is unavailable.

## Independent verification

- Population: 624 cases
- Independently recalculated: 89 cases (14.26%)
- Valid cases sampled: 65
- Invalid/guard cases sampled: 24
- Arithmetic: exact rational numbers (`Fraction`) with a separately implemented HALF_UP quantizer
- Shared production code: none
- Disagreements: 0

## Stratification

```json
{
  "BOUNDARY_CASE": 59,
  "EFFECTIVE_DATE": 1,
  "INVALID_INPUT": 24,
  "LEGACY_ADAPTER": 1,
  "NORMAL_CASE": 1,
  "ROUNDING_SENSITIVE": 1,
  "RULE_INTERACTION": 1,
  "ZERO_VALUE": 1
}
```

Sampled rows are marked `INDEPENDENTLY_VERIFIED`; remaining rows are `POLICY_DERIVED`. No case is marked `ADJUDICATED`.
