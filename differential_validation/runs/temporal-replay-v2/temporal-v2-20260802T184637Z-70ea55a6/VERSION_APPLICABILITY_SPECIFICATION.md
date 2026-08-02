# Version Applicability Specification

Allowed states are `APPLICABLE_MATCHED`, `APPLICABLE_MISMATCHED`, `APPLICABLE_MISSING`, `NOT_APPLICABLE`, `UNRESOLVED`, and `MEASUREMENT_FAILED`. Applicable identities require non-empty expected/resolved IDs. `NOT_APPLICABLE` requires empty IDs and a null comparison result; it is excluded from match denominators. Missing applicable evidence fails the run.
