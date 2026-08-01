
# Full-pipeline E2E audit

The suite contains 36 traces, but the evidence supports 32 true full-payroll transactions and 4 Laravel configuration guards. The guards terminate before HTTP and are not cosmetically counted as full pipeline.

| Evaluation category | Cases |
|---|---|
| FULL_PAYROLL_PIPELINE | 32 |
| LARAVEL_CONFIGURATION_GUARD | 4 |

Each full-pipeline trace records testing database fixtures, `buildFactsFromDatabase`, `PayrollRuleEngineService::execute`, Go `/execute`, GRULE, normalization, component hashes, salary persistence, and database assertion. Go request IDs remain `NOT_OBSERVABLE`; request/response hashes provide the available correlation evidence.
