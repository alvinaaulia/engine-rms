# Corpus category specification

| Category | Predicate | Treatment evidence |
|---|---|---|
| NORMAL_CASE | Valid, no boundary, no interaction, canonical route | GENERAL_VALID_PAYROLL |
| BOUNDARY_CASE | At least one declared B-1/B/B+1 boundary | treatment_parameters.boundaries |
| ROUNDING_SENSITIVE | Raw value below/at/above six-decimal HALF_UP tie | rounding_probe |
| LEGACY_ADAPTER | Request is actually sent through legacy rules payload | execution_route=LEGACY_ADAPTER |
| RULE_INTERACTION | At least two rules match | matched_rule_count>=2 |
| INVALID_INPUT | Structured rejection and expected error code | validity=INVALID |
| EFFECTIVE_DATE | Before, at, or during effective period | effective_from/position |
| ZERO_VALUE | All attendance adjustments explicitly zero | ZERO_ATTENDANCE_ADJUSTMENTS |
