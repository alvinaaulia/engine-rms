# Differential Validation Final Report

## 1. Executive verdict

The frozen reference oracle and the Laravel-to-Go TPR-IR/GRULE implementation agree for all 624 corpus cases after one validator defect was fixed. Final result: **624/624 exact cases, 2,594/2,594 exact component comparisons, 3,600/3,600 exact summary comparisons, and 0 unresolved mismatches**.

This is a reference-oracle result, not an authoritative HRD payroll certification. The cited HRD spreadsheet was not available.

## 2. Frozen baseline

- Tag: `tpr-ir-differential-baseline-v1`
- Laravel baseline: `ca16f0500d8404cecaca03950cfc252072ca3e23`
- Go baseline: `1dcad9df1be852263590fd23ab11ce569ea1c99e`
- Policy: `reference-payroll-2026.1`, scale 6, HALF_UP
- Frozen expected SHA-256: `420ea99382917416abb471ad22e3efe06aeac43f6ec575dc5220e0a16745ac51`

## 3. Domain inventory

The experiment uses 11 active rule versions, 10 real component codes, real employee/attendance fields, 12 rate keys, component taxability, priorities, effective periods, and only supported operators/formulas. See `PAYROLL_DOMAIN_DICTIONARY.md`.

## 4. Corpus composition

| Primary category | Cases | Exact rate |
|---|---:|---:|
| BOUNDARY | 67 | 100.00% |
| EFFECTIVE_DATE | 66 | 100.00% |
| LEGACY_ADAPTER | 65 | 100.00% |
| NEGATIVE_INVALID_GUARD | 24 | 100.00% |
| NORMAL | 66 | 100.00% |
| RATE_TAX_VARIATION | 68 | 100.00% |
| ROUNDING_SENSITIVE | 67 | 100.00% |
| RULE_INTERACTION | 68 | 100.00% |
| TPR_IR_CANONICAL | 65 | 100.00% |
| ZERO_VALUE | 68 | 100.00% |

Total: 50 anonymous profiles × 12 periods = 600 valid cases, plus 24 invalid guard cases.

## 5. Oracle construction

The primary oracle is a standalone Python Decimal evaluator with explicit business formulas and intermediate traces. It imports no Laravel/Go calculation code, does not use TPR-to-GRL, and does not use GRULE.

## 6. Oracle verification

An independent Fraction-based verifier recalculated 84/624 cases (13.46%), including all 24 invalid cases. Disagreements: 0. Sampled cases are `VERIFIED`; remaining cases are `ADJUDICATED` under the same frozen policy.

## 7. Differential results

- Executed: 624
- Successful valid cases: 600
- Correct structured rejections: 24
- Comparison records: 6842
- Final mismatches: 0

## 8. Exact-match metrics

| Metric | Result |
|---|---:|
| Exact cases | 624/624 (100.00%) |
| Exact component rows | 2594/2594 (100.00%) |
| Exact summary rows | 3600/3600 (100.00%) |
| Provenance match | 2594/2594 (100.00%) |
| Mean absolute monetary error | 0.000000 |
| Maximum absolute monetary error | 0.000000 |
| Relative error for non-zero denominator | 0.000000 |
| Runtime error rate | 0/624 (0.00%) |
| Timeout rate | 0/624 (0.00%) |

Every component code and every primary boundary/rounding category has zero final mismatch.

## 9. Mismatch categories

| Category | Final count |
|---|---:|
| `MISSING_COMPONENT` | 0 |
| `UNEXPECTED_COMPONENT` | 0 |
| `COMPONENT_TYPE_MISMATCH` | 0 |
| `RAW_AMOUNT_MISMATCH` | 0 |
| `ROUNDED_AMOUNT_MISMATCH` | 0 |
| `TAXABLE_BASE_MISMATCH` | 0 |
| `TAX_MISMATCH` | 0 |
| `GROSS_MISMATCH` | 0 |
| `DEDUCTION_MISMATCH` | 0 |
| `NET_MISMATCH` | 0 |
| `ROUNDING_POINT_MISMATCH` | 0 |
| `RULE_PROVENANCE_MISMATCH` | 0 |
| `RATE_VERSION_MISMATCH` | 0 |
| `TRANSLATION_MISMATCH` | 0 |
| `ORACLE_DISPUTE` | 0 |
| `RUNTIME_ERROR` | 0 |
| `TIMEOUT` | 0 |

## 10. Root-cause findings

The initial run found 8 invalid-basic-salary cases accepted as success. Root cause: formula identifiers were checked for presence but not runtime fact type when absent from condition nodes. Expected data was not modified.

## 11. Fixes and regression tests

`ValidateTPRRuleSet` now applies `strictScalar` to every formula fact. The failing regression test was added before the fix. The full corpus then changed from 8 mismatched cases to 0. TPR eligibility fields used by active rules were also added consistently to the Laravel and Go catalogs.

## 12. Reproducibility status

`run_differential.ps1` performs guarded testing-database migration/seed, regenerates and independently freezes the oracle, produces translation fixtures, starts the current Go engine, runs the differential runner, runs full Laravel/Go suites and vet, regenerates reports, and returns non-zero on any mismatch/failure.

The verified one-command run completed successfully in 354.4 seconds. Final suites: Laravel 156 tests/837 assertions PASS, Go full suite PASS, and `go vet ./...` PASS.

## 13. Remaining limitations

- No HRD/domain expert or cited spreadsheet was available; therefore the oracle is `FROZEN_REFERENCE_ONLY`.
- The Go response exposes rounded component amounts, not pre-rounding raw candidate amounts or rounding-point events. Raw values exist in oracle traces, but end-to-end raw/rounding-point equality is not externally observable through the current API.
- The corpus validates the audited synthetic domain and frozen policy, not historical production replay or temporal data drift.
- No active company tax configuration existed; tax behavior here is the audited `TAX_FLAT` rule with deterministic synthetic rate variants.

## 14. Readiness for the next stage

**C. Differential validation selesai dan siap ke temporal replay testing.**

Expected results were independently verified and frozen before production comparison, all final component/summary/provenance comparisons match, and no unresolved mismatch remains. Option D is intentionally not selected because HRD authority and temporal replay evidence are still absent.
