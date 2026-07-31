# Mismatch Root-Cause Report

## Summary

The first complete run executed all 624 cases and found 8 mismatched cases. Expected results were not changed. All eight cases used an invalid string for `employee.basic_salary`; the engine accepted it as zero because a numeric fact referenced only by a formula was checked for presence, not type.

The defect was reproduced with a single canonical case, a failing regression test was added first, production validation was fixed in `tpr_ir.go`, and the full 624-case corpus was rerun. The final run has 0 mismatches.

| Case ID | Expected | Actual | Category | Root Cause | Fix | Regression Test | Status |
|---|---|---|---|---|---|---|---|
| `INVALID-002` | reject `INVALID_FACT_TYPE` | success | `RUNTIME_ERROR` (guard bypass) | Formula facts checked for presence but not runtime type | Validate every formula identifier with `strictScalar` | `TestTPRSchemaAndTrustBoundaryValidation/invalid_formula_fact_type` | RESOLVED |
| `INVALID-005` | reject `INVALID_FACT_TYPE` | success | `RUNTIME_ERROR` (guard bypass) | Formula facts checked for presence but not runtime type | Validate every formula identifier with `strictScalar` | `TestTPRSchemaAndTrustBoundaryValidation/invalid_formula_fact_type` | RESOLVED |
| `INVALID-008` | reject `INVALID_FACT_TYPE` | success | `RUNTIME_ERROR` (guard bypass) | Formula facts checked for presence but not runtime type | Validate every formula identifier with `strictScalar` | `TestTPRSchemaAndTrustBoundaryValidation/invalid_formula_fact_type` | RESOLVED |
| `INVALID-011` | reject `INVALID_FACT_TYPE` | success | `RUNTIME_ERROR` (guard bypass) | Formula facts checked for presence but not runtime type | Validate every formula identifier with `strictScalar` | `TestTPRSchemaAndTrustBoundaryValidation/invalid_formula_fact_type` | RESOLVED |
| `INVALID-014` | reject `INVALID_FACT_TYPE` | success | `RUNTIME_ERROR` (guard bypass) | Formula facts checked for presence but not runtime type | Validate every formula identifier with `strictScalar` | `TestTPRSchemaAndTrustBoundaryValidation/invalid_formula_fact_type` | RESOLVED |
| `INVALID-017` | reject `INVALID_FACT_TYPE` | success | `RUNTIME_ERROR` (guard bypass) | Formula facts checked for presence but not runtime type | Validate every formula identifier with `strictScalar` | `TestTPRSchemaAndTrustBoundaryValidation/invalid_formula_fact_type` | RESOLVED |
| `INVALID-020` | reject `INVALID_FACT_TYPE` | success | `RUNTIME_ERROR` (guard bypass) | Formula facts checked for presence but not runtime type | Validate every formula identifier with `strictScalar` | `TestTPRSchemaAndTrustBoundaryValidation/invalid_formula_fact_type` | RESOLVED |
| `INVALID-023` | reject `INVALID_FACT_TYPE` | success | `RUNTIME_ERROR` (guard bypass) | Formula facts checked for presence but not runtime type | Validate every formula identifier with `strictScalar` | `TestTPRSchemaAndTrustBoundaryValidation/invalid_formula_fact_type` | RESOLVED |

## Layer attribution

- Source facts: intentionally invalid and correct for negative testing.
- Laravel adapter/canonicalization: not causal; the invalid fact was preserved on the wire.
- Go validator: root cause.
- Formula AST, GRL emission, GRULE execution, candidate resolution, rounding, and summary: not causal.
- Oracle: independently verified and unchanged.

## Before/after

| Run | Cases | Mismatched cases | Mismatches | Status |
|---|---:|---:|---:|---|
| Initial post-freeze run | 624 | 8 | 8 | Failed |
| After validator fix | 624 | 0 | 0 | Passed |

The historical mismatch remains documented even though `mismatch_details.json` represents the final clean run.
