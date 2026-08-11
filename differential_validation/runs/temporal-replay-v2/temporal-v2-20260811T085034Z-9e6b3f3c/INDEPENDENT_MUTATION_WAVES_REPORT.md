# Independent Mutation Waves Report

All ten waves started from the same baseline SHA-256 `5cdc3f9393bec087c5c24f49db30948e98321e8b3b8be1c9b6047390df814aad`. Each mutation ran in a nested database transaction and was rolled back before the next wave.

| Wave | Mutation | Baseline execution | Mutated execution | Result |
|---|---|---|---|---|
| I-WAVE-01 | rule_formula_and_version_changed | SUCCESS | SUCCESS | PASS |
| I-WAVE-02 | rate_version_changed | SUCCESS | SUCCESS | PASS |
| I-WAVE-03 | tax_version_changed | SUCCESS | SUCCESS | PASS |
| I-WAVE-04 | employee_salary_and_contract_changed | SUCCESS | SUCCESS | PASS |
| I-WAVE-05 | rounding_policy_changed | SUCCESS | SUCCESS | PASS |
| I-WAVE-06 | current_rule_disabled | SUCCESS | EXPECTED_REJECTION | PASS |
| I-WAVE-07 | translator_or_engine_compatibility_changed | SUCCESS | EXPECTED_REJECTION | PASS |
| I-WAVE-08 | current_attendance_corrected | SUCCESS | SUCCESS | PASS |
| I-WAVE-09 | current_tax_configuration_removed | SUCCESS | SUCCESS | PASS |
| I-WAVE-10 | current_rate_reference_unavailable | SUCCESS | EXPECTED_REJECTION | PASS |

Independent waves are the only evidence used to attribute an effect to one mutation.
