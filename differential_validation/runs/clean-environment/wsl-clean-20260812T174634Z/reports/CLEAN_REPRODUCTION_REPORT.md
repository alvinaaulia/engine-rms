# Clean-environment research evidence

## Verdict

The isolated `WSL_NATIVE` reproduction completed with status `PASS` and exit code `0`. Source snapshot, environment preparation, service readiness, frozen-hash verification, reconstructed baseline, fixed differential validation, translator validation, full-pipeline validation, configuration guards, schema validation, and report generation all completed successfully.

## Frozen source pair

- Rule engine and evidence package: `574a43a5e93483e0ad685cb85da01b0dd8737a83`
- Laravel web application: `e211d1666c460842970aeb7b1e38af362308ea94`
- Runner: `DESKTOP-GNR1KF4`, Ubuntu 26.04 LTS on WSL2 (`x86_64`)
- Toolchain: Go 1.25.6, PHP 8.5.4, Composer 2.9.5, Python 3.14.4, MySQL client 8.4.10 and MySQL server 8.0.30
- Started: `2026-08-12T17:46:34Z`
- Finished: `2026-08-12T18:10:14Z`
- Duration: `1421` seconds

Both repositories were cloned into a temporary isolated snapshot at the commit IDs above. The recorded source identities show clean working trees before dependency installation and experiment execution.

## Reproduced results

| Evaluation | Cases/comparisons | Result |
|---|---:|---|
| Reconstructed baseline, repeat 1 | 624 / 6,832 | 8 mismatches across 8 cases |
| Reconstructed baseline, repeat 2 | 624 / 6,832 | 8 mismatches across the same 8 cases |
| Fixed differential | 624 / 6,840 | 0 mismatches across 0 cases |
| Full payroll pipeline | 32 transactions | 32 exact matches and 32 persistence assertions |
| Configuration guards | 4 invalid configurations | 4 expected rejections; database unchanged |
| Full-pipeline PHPUnit | 1 test / 750 assertions | 0 failures and 0 errors |
| Full Laravel suite | 1,638 assertions | 0 assertion failures |
| Final artifact validator | 28 artifacts | `PASS` |

The reconstructed mismatch IDs were stable across both repetitions: `INVALID-002`, `INVALID-005`, `INVALID-008`, `INVALID-011`, `INVALID-014`, `INVALID-017`, `INVALID-020`, and `INVALID-023`. The fixed run used the same frozen corpus, expected results, and policy hashes as the baseline reconstruction.

PHP 8.5 emitted deprecation notices from dependencies during the Laravel suite. These were non-failing compatibility notices, not failed assertions; the project target remains PHP 8.4.

## Claim boundary

This run supports clean-environment reproducibility and technical equivalence against the frozen reference oracle. It does not establish that the frozen oracle is an authoritative payroll, legal, or regulatory oracle. Domain-expert validation remains a separate requirement.

Temporal replay v2 was not executed as part of this run and remains `NOT_STARTED` in `manifest.json`. This report therefore makes no new temporal-replay claim.

## Machine-readable evidence

- `manifest.json`: final run gate
- `command-results.json`: recorded command outcomes and log references
- `environment.json`: isolated runner identity
- `reconstructed-baseline/manifest.json`: repeated baseline provenance
- `fixed/manifest.json`: fixed source, environment, and frozen hashes
- `fixed/mismatch_details.json`: zero-mismatch result
- `fixed/full_pipeline_e2e.json`: full-pipeline and persistence traces
- `e2e/e2e-execution-traces.json`: per-case execution path and hashes
- `raw-logs/`: source identity, service, tool-version, test, and validation logs
