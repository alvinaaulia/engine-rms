
# Report generator audit

The reporting chain parses raw command metadata, JUnit XML, and Go JSON events; validates schemas and hashes; derives counts from artifacts; writes `final-report-data.json`; and rejects report/artifact count disagreement. No fallback PASS, test count, mismatch count, assertion count, or duration is used.

| Evidence parser | Tests | Failed | Exit | Duration seconds | Raw metadata |
|---|---|---|---|---|---|
| Laravel full suite | 157 | 0 | 0 | 138.640974 | laravel-tests-hardening.xml |
| Go full suite | 204 | 0 | 0 | 13.852348 | go-tests-hardening.stdout.log |
| Go vet | N/A | N/A | 0 | 16.270726 | go-vet-hardening.stdout.log |
| Translator fixtures | 13 | 0 | 0 | 45.367986 | translator-hardening.stdout.log |
| Laravel E2E suite | 1 | 0 | 0 | 25.872014 | e2e-hardening-junit.xml |
| Corpus generation | N/A | N/A | 0 | 1.345525 | corpus-generation.stdout.log |
| Oracle generation | N/A | N/A | 0 | 0.643492 | oracle-generation.stdout.log |
| Oracle verification | N/A | N/A | 0 | 1.199619 | oracle-verification.stdout.log |
| Reconstructed baseline repeat 1 | N/A | N/A | 0 | 19.492545 | differential.stdout.log |
| Reconstructed baseline repeat 2 | N/A | N/A | 0 | 18.916938 | differential.stdout.log |
| Fixed differential | N/A | N/A | 0 | 20.751661 | differential-hardening.stdout.log |

Regression tests cover missing evidence, malformed JSON/logs, duplicate IDs, hash mismatch, stale metadata, failed tests, missing exit code, manual PASS, invalid metric nullability, unsupported adjudication, incomplete E2E paths, false ORIGINAL baselines, and inconsistent report counts.
