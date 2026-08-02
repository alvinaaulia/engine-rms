# Differential validation final report V4

## Executive verdict

The clean WSL-native reproduction is `PASS`. Decision: **J — clean reproduction passed while domain validation remains pending**. This decision does not promote the reference oracle into an authoritative payroll/business oracle.

## Source and runner

Engine/validation commit `069581549fadaa8f74281722592c5bfa68ae4053` and Laravel commit `269c6a656804c9ef11078539d65850f93a23f577` were selected through tag `tpr-ir-clean-closure-v4` in clean source clones. The workload ran under WSL 2 native Ubuntu; Docker was not used.

## Differential and integration results

| Evaluation layer | Independent cases | Assertion layer | Mismatch/failure | Status |
|---|---:|---|---:|---|
| Reconstructed baseline, repeat 1 | 624 | differential comparison | 8 | RECONSTRUCTED_REPRODUCED |
| Reconstructed baseline, repeat 2 | 624 | differential comparison | 8 | RECONSTRUCTED_REPRODUCED |
| Fixed differential | 624 | differential comparison | 0 | PASS |
| Translator | 12 | fixture subtests | 0 | PASS |
| Full payroll pipeline | 32 | persistence on the same 32 transactions | 0 | PASS |
| Configuration guards | 4 | expected rejection before Go | 0 | PASS |

The stable reconstructed-baseline mismatch IDs are `INVALID-002, INVALID-005, INVALID-008, INVALID-011, INVALID-014, INVALID-017, INVALID-020, INVALID-023`. The original historical raw baseline remains unavailable; these are two newly executed reconstruction runs and are not presented as the original run.

The E2E artifact contains 36 traces in total: 32 full payroll transactions plus 4 configuration guards. The guards are not counted as transactions. The dedicated PHPUnit wrapper contains one test method with 750 assertions; the trace artifact is the case-level evidence for the 32 + 4 split.

## Exactness and observability

Fixed execution achieved 624/624 case exact matches, 2592/2592 component exact matches, and 3600/3600 summary exact matches, with zero runtime errors and zero timeouts. Sixteen metrics are measured. Four are `NOT_OBSERVABLE`: raw amount, exact rounding point, resolved rate-version identity, and resolved tax-version identity. Translation and persistence metrics are `NOT_APPLICABLE` inside the differential layer because they are evaluated by their dedicated layers.

## Test-suite evidence

The full Laravel JUnit result is 157 tests, 1587 assertions, 0 failures, 0 errors, and 0 skipped; the console reports 155 passed and 2 deprecated. Translator evidence is 12 fixture subtests, not 13 independent tests (the additional Go event is the parent test). Go package tests and `go vet ./...` both exited 0.

## Hash and domain status

Frozen policy `1edaaed6094facf558de01e741f12beb0ac3a828d950c2d7ab8e58d2da9ddca1`, corpus `08f16457e2ba3a3ce614ba4e71d9d2629f496c9249c43fe6b09828618161f011`, and expected-results `e6d5a74fef5b739134796bb83b41641d155160d16fe563276fc4f57940d9e91c` matched both the checked source and clean readiness log. Output hashes are recorded in `CLEAN_HASH_VERIFICATION_REPORT.json`.

Domain status remains `NOT_AUTHORITATIVE_BUSINESS_ORACLE / DOMAIN_VALIDATION_PENDING`. Temporal replay remains `NOT_STARTED`.

## Limitations

- The WSL base distribution and Windows MySQL server were pre-existing; isolation/freshness applies to the workload and dedicated test schema, not to a new VM.
- The database server version, CPU model, available memory, and peak memory were not recorded during the run.
- No Docker image digest exists because the user-selected path intentionally did not use Docker.
- Private-source access proves reproducibility from an already-authorized local repository snapshot, not anonymous remote clone access.
