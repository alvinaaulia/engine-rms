
# Automated evidence generation report

| Command | Status | Tests | Passed | Failed | Assertions | Duration seconds | Exit | Evidence |
|---|---|---|---|---|---|---|---|---|
| Laravel full suite | PASS | 157 | 157 | 0 | 1583 | 172.729253 | 0 | laravel-tests-hardening.xml |
| Go full suite | PASS | 204 | 204 | 0 | N/A | 13.852348 | 0 | go-tests-hardening.stdout.log |
| Go vet | PASS | N/A | N/A | N/A | N/A | 16.270726 | 0 | go-vet-hardening.stdout.log |
| Translator fixtures | PASS | 13 | 13 | 0 | N/A | 45.367986 | 0 | translator-hardening.stdout.log |
| Laravel E2E suite | PASS | 1 | 1 | 0 | 746 | 49.184512 | 0 | e2e-hardening-junit.xml |
| Corpus generation | PASS | N/A | N/A | N/A | N/A | 1.345525 | 0 | corpus-generation.stdout.log |
| Oracle generation | PASS | N/A | N/A | N/A | N/A | 0.643492 | 0 | oracle-generation.stdout.log |
| Oracle verification | PASS | N/A | N/A | N/A | N/A | 1.199619 | 0 | oracle-verification.stdout.log |
| Reconstructed baseline repeat 1 | PASS | N/A | N/A | N/A | N/A | 19.492545 | 0 | differential.stdout.log |
| Reconstructed baseline repeat 2 | PASS | N/A | N/A | N/A | N/A | 18.916938 | 0 | differential.stdout.log |
| Fixed differential | PASS | N/A | N/A | N/A | N/A | 20.751661 | 0 | differential-hardening.stdout.log |

All values above are parsed from raw metadata/logs. Generator and validator unit tests are executed separately by the one-command runner and must exit zero before report generation.
