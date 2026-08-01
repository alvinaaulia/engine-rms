
# Evidence integrity audit

| Claim | Value | Evidence | Status |
|---|---|---|---|
| Corpus cases | 624 | oracle_input_cases.json | VERIFIED_FROM_RAW_EVIDENCE |
| Independently verified | 89 | oracle_expected_results.json | VERIFIED_FROM_RAW_EVIDENCE |
| Policy-derived | 535 | oracle_expected_results.json | VERIFIED_FROM_RAW_EVIDENCE |
| Reconstructed baseline mismatches | 8 | runs/reconstructed-baseline/manifest.json | RECONSTRUCTED |
| Fixed mismatches | 0 | runs/fixed/mismatch_details.json | VERIFIED_FROM_RAW_EVIDENCE |
| Translator fixtures | 12 | translation_validation_fixtures.json | VERIFIED_FROM_RAW_EVIDENCE |
| Translator failed test events | 0 | runs/hardening/raw-logs/translator-hardening.stdout.log | VERIFIED_FROM_RAW_EVIDENCE |
| E2E suite cases | 36 | e2e-execution-traces.json | VERIFIED_FROM_RAW_EVIDENCE |
| Full payroll pipeline cases | 32 | e2e-execution-traces.json | VERIFIED_FROM_RAW_EVIDENCE |
| Configuration guard cases | 4 | e2e-execution-traces.json | VERIFIED_FROM_RAW_EVIDENCE |
| Persistence E2E transactions | 32 | e2e-execution-traces.json | VERIFIED_FROM_RAW_EVIDENCE |
| Laravel tests | 157 | runs/hardening/raw-logs/laravel-tests-hardening.xml | VERIFIED_FROM_RAW_EVIDENCE |
| Laravel assertions | 1587 | runs/hardening/raw-logs/laravel-tests-hardening.xml | VERIFIED_FROM_RAW_EVIDENCE |
| Go tests | 204 | runs/hardening/raw-logs/go-tests-hardening.stdout.log | VERIFIED_FROM_RAW_EVIDENCE |
| Domain validation sample | 89 | DOMAIN_VALIDATION_SAMPLE.csv | VERIFIED_FROM_RAW_EVIDENCE |
| Clean environment | NOT_EXECUTED | REPRODUCIBILITY_MANIFEST.json | NOT_APPLICABLE |

- Inventoried files: 341 (structured source: `ARTIFACT_INVENTORY.json`).
- Duplicate case IDs, frozen hashes, per-case hashes, manifest hashes, metric nullability, E2E paths, command exit evidence, and report counts are enforced by `validate_artifacts.py`.
- Reconstructed evidence is never labeled original. A command is PASS only when its recorded exit code and parsed result support PASS.
