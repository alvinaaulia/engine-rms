
# Full-pipeline Laravel–Go E2E report

Validation type: `FULL_PIPELINE_END_TO_END_VALIDATION`.

| Measure | Value |
|---|---|
| Cases | 36 |
| Exact valid results | 32 |
| Expected configuration rejections | 4 |
| Unexpected mismatch | 0 |
| Persisted salary records | 32 |
| Runtime failures | 0 |

The valid path is testing database → attendance/overtime records → `buildFactsFromDatabase` → `PayrollRuleEngineService::execute` → Go HTTP `/execute` → GRULE → Laravel normalization/provenance → salary persistence. The subset covers salary, attendance, overtime, deduction, bonus, tax, rate dependencies, formulas, approval/active validation, provenance, six-decimal rounding, and invalid configuration rejection.

Translator validation is separate: `12` fixture records were exercised by 13 Go test events with 0 failure. It is not merged into the E2E case count.
