# Service readiness report V4

| Service | Readiness result | Observed evidence |
|---|---|---|
| MySQL | PASS | server responded; dedicated database `website_papa_v2_wsl_clean_testing`; collation `utf8mb4_0900_ai_ci` |
| Laravel | PASS | Laravel 10.50.2 booted with environment `testing`; PHP 8.5.4 |
| Go rule engine | PASS | go version go1.25.6 linux/amd64 and HTTP `/health` readiness gate passed |
| Frozen inputs | PASS | policy, corpus, and expected-result hashes matched the frozen manifest |
| Validation runner | PASS | all 19 recorded commands exited 0 |

Raw readiness evidence: `runs/clean-environment/wsl-clean-20260802T090158Z/raw-logs/service-health.log`.
