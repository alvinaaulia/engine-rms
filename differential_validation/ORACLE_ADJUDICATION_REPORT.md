# Oracle Adjudication Report

## Decision

Status: **FROZEN_REFERENCE_ONLY**. The expected results are technically frozen for the experiment; they are not asserted as HRD-authoritative because the cited HRD spreadsheet is unavailable.

## Independent verification

- Population: 624 cases
- Independently recalculated: 84 cases (13.46%)
- Valid cases sampled: 60
- Invalid/guard cases sampled: 24
- Arithmetic: exact rational numbers (`Fraction`) with a separately implemented HALF_UP quantizer
- Shared production code: none
- Disagreements: 0

## Stratification

```json
{
  "BOUNDARY": 7,
  "EFFECTIVE_DATE": 7,
  "LEGACY_ADAPTER": 7,
  "NEGATIVE_INVALID_GUARD": 24,
  "NORMAL": 8,
  "RATE_TAX_VARIATION": 6,
  "ROUNDING_SENSITIVE": 6,
  "RULE_INTERACTION": 6,
  "TPR_IR_CANONICAL": 7,
  "ZERO_VALUE": 6
}
```

Sampled rows are marked `VERIFIED`; the remaining rows are marked `ADJUDICATED` under the same frozen policy.
