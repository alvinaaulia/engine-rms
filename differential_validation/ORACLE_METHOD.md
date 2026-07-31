# Oracle Method

## Classification

Oracle status: **FROZEN_REFERENCE_ONLY**. It is independent of the implementation under test but is not described as HRD-authoritative because the referenced payroll spreadsheet is unavailable.

## Primary evaluator

`oracle_calculator/reference_oracle.py` is a standalone Python calculator that:

- imports no Laravel or Go production code;
- does not use GRULE or the TPR-to-GRL translator;
- expresses each audited rule directly as documented business logic;
- uses Python `Decimal` with precision 50;
- applies six-decimal `ROUND_HALF_UP` at candidate, COLLECT_SUM, and summary points;
- produces component, raw amount, rounded amount, source-rule provenance, summary, taxability, and formula/input traces;
- emits deterministic JSON and CSV.

Formula source is the active database rule inventory frozen in `reference_policy.json`. Each valid result records creator, formula source, rounding policy, trace inputs/results, and domain-verification status. Invalid results record the expected structured rejection.

## Summary calculation

- `gross_salary = basic_salary + sum(EARNING components)`.
- `total_deductions = sum(DEDUCTION components)`.
- `net_salary = gross_salary - total_deductions`.
- `taxable_amount = basic_salary + sum(taxable EARNING components)`.
- `tax = TAX_FLAT amount`.

Components are aggregated by code under COLLECT_SUM and retain contributor IDs/version IDs.

## Independent verifier

`oracle_calculator/verify_oracle.py` does not import the primary oracle. It uses exact `Fraction` arithmetic and a separately implemented integer HALF_UP quantizer. It recalculates every tenth valid case plus all invalid guards: 84/624 cases (13.46%).

The verifier compares execution status/error, components, exact raw numeric values, rounded values, provenance, and summary. The completed review found zero disagreement. Sampled cases are marked VERIFIED; remaining cases are ADJUDICATED under the same frozen rule policy.

## Freeze controls

After successful verification, the verifier:

1. marks the expected dataset `FROZEN_REFERENCE_ONLY`;
2. writes the verification counts;
3. hashes `reference_policy.json`, `oracle_input_cases.json`, and `oracle_expected_results.json`;
4. writes `.oracle_frozen.json`;
5. prevents the production runner from starting if any frozen hash changes.

Expected data was frozen before the first production differential request. The later production bug fix did not change the oracle or frozen hashes.
