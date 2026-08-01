
# Bug discovery and remediation report

The reconstructed baseline produced 8 mismatches across 8 cases: INVALID-002, INVALID-005, INVALID-008, INVALID-011, INVALID-014, INVALID-017, INVALID-020, INVALID-023. The formula field was checked for existence, but referenced fact runtime types were not validated; invalid `employee.basic_salary` types therefore reached execution. The fix validates formula fact runtime types before GRULE execution.

Each case is preserved under `bug_evidence/<case-id>/` with input, unchanged expected output, baseline actual, fixed actual, root cause, and the regression-test reference. The fixed run produced 0 mismatch. The oracle expected artifact hash stayed frozen for both runs.
