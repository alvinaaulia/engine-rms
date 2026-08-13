# Cumulative Mutation Waves Report

The retained v1 mutation experiment is explicitly classified as `CUMULATIVE_MUTATION_WAVES`. State produced by one wave is the input to the next and is not independent-effect evidence.

| Wave | Mutation | Inherits prior state | Result |
|---|---|---:|---|
| C-WAVE-01 | rule_formula_and_version | false | PASS |
| C-WAVE-02 | rate_version | true | PASS |
| C-WAVE-03 | tax_version | true | PASS |
| C-WAVE-04 | employee_salary_and_contract | true | PASS |
| C-WAVE-05 | rounding_policy | true | PASS |
| C-WAVE-06 | current_rule_disabled | true | PASS |
| C-WAVE-07 | translator_engine_compatibility | true | PASS |
