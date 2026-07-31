# Corpus Design

## Population

- Deterministic seed: `20260801`.
- 50 anonymous synthetic employee profiles.
- 12 payroll periods from January through December 2026.
- 600 valid profile-period cases.
- 24 negative guard cases.
- Total: 624 stable case IDs.

Valid IDs follow `PAY-<profile>-<period>`; invalid IDs follow `INVALID-<sequence>`. The generator is `generate_corpus.py` and emits both JSON and CSV.

## Primary strata

| Stratum | Cases |
|---|---:|
| NORMAL | 66 |
| BOUNDARY | 67 |
| ZERO_VALUE | 68 |
| NEGATIVE_INVALID_GUARD | 24 |
| RULE_INTERACTION | 68 |
| RATE_TAX_VARIATION | 68 |
| ROUNDING_SENSITIVE | 67 |
| EFFECTIVE_DATE | 66 |
| LEGACY_ADAPTER | 65 |
| TPR_IR_CANONICAL | 65 |

Tags provide overlapping coverage for permanent/freelancer status, performance boundaries, decimal boundaries, and zero boundaries.

## Boundary strategy

- Performance bands: 69/70/71, 79/80/81, and 89/90/91.
- Overtime: 0/1 and 59/60/61 minutes.
- Attendance deductions/incentive: zero, one unit, and positive values.
- Eligibility: both boolean states and combinations.
- Decimal money: values just below, at, and above six-decimal HALF_UP ties.
- Effective date: periods before/at/after active rule start and the bounded freelancer-rate interval.
- Tax/rate: zero, normal, positive, and decimal-sensitive flat tax/rates.

The corpus does not create rules for unsupported paid leave, generic allowances, or `CMP_LEMBUR_FREELANCER`; the latter exists as an active component/rate but has no active rule producer in the audited rule set.

## Invalid guards

All 24 guard cases remain in the corpus:

- 8 missing `employee.status` → `MISSING_REQUIRED_FACT`.
- 8 invalid `employee.basic_salary` type → `INVALID_FACT_TYPE`.
- 8 invalid eligibility-flag type → `INVALID_FACT_TYPE`.

The invalid-basic-salary stratum found a real validator defect and was never removed or altered.

## Determinism and independence

Corpus generation uses no production output. Expected results are computed only after inputs are persisted, then independently verified and frozen. The production runner refuses to execute if policy/input/expected hashes differ from `.oracle_frozen.json`.
