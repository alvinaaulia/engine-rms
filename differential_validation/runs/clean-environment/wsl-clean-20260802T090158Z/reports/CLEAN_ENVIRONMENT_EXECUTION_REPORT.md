# Clean-environment execution report V4

## Outcome

Run `wsl-clean-20260802T090158Z` completed with status `PASS` and exit code `0` in 1912 seconds. It used WSL 2 native Ubuntu without Docker.

## Environment and freshness

| Field | Recorded value |
|---|---|
| OS / architecture | Ubuntu 26.04 LTS WSL2 6.18.33.2-microsoft-standard-WSL2 / x86_64 |
| Timezone / locale | Asia/Jakarta (`WIB`) / C.UTF-8 |
| PHP / Composer | 8.5.4 / 2.9.5 |
| Go / Python | 1.25.6 / 3.14.4 |
| MySQL client | 8.4.10 |
| Database | fresh dedicated schema `website_papa_v2_wsl_clean_testing` |
| Database collation / server timezone | utf8mb4_0900_ai_ci / SYSTEM |
| CPU / memory / peak memory | NOT_RECORDED / NOT_RECORDED / NOT_MEASURED |
| Container images | NOT_APPLICABLE; no Docker images were used |

Freshness applies to the workload, source clones, dependency environments/caches, and test database schema. The WSL distribution and Windows MySQL server were pre-existing shared infrastructure. The database server version was not recorded during this run; only the MySQL client version was recorded.

## Executed validation

| Layer | Result |
|---|---|
| Reconstructed baseline | PASS: two repeats, 624 cases each, stable 8 mismatches |
| Fixed differential | PASS: 624 cases, 0 mismatches |
| Translator | PASS: 12 fixtures, 0 failures |
| Full payroll pipeline | PASS: 32 independent transactions, 0 mismatches; persistence asserted on the same 32 |
| Configuration guards | PASS: 4 expected pre-Go rejections; not payroll transactions |
| Full Laravel suite | PASS: 157 tests, 1587 assertions, 0 failures/errors/skips; console classified 155 passed and 2 deprecated |
| Go tests / vet | PASS / PASS; Go JSON contains 207 terminal pass events including parent and subtest nodes |
| Schema validation / report generation | PASS / PASS |

All 19 recorded commands and their timestamps, durations, streams, and exit codes are in `runs/clean-environment/wsl-clean-20260802T090158Z/command-results.json`. Temporal replay remains `NOT_STARTED`.
