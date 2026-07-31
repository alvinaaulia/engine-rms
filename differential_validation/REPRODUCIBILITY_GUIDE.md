# Reproducibility Guide

## Prerequisites

- Windows PowerShell, Git Bash optional.
- PHP/Laravel dependencies installed in `C:\PROJECT\papa-website-v2`.
- Go dependencies available for `C:\PROJECT\engine-rms`.
- Python 3.
- MySQL running, with a disposable database named `website_papa_v2_testing`.
- Port 8081 free or occupied only by a prior `rule-engine`/`differential-engine` test process.

The script has a hard guard requiring the database name to end in `_testing` before `migrate:fresh`.

## One command

From `C:\PROJECT\engine-rms` in Git Bash:

```bash
powershell.exe -ExecutionPolicy Bypass -File ./differential_validation/run_differential.ps1
```

Or from PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\differential_validation\run_differential.ps1
```

## What the command does

1. Forces the isolated `website_papa_v2_testing` environment.
2. Runs fresh migrations and `DatabaseSeeder`.
3. Regenerates the 624-case deterministic corpus.
4. Regenerates the independent Decimal reference oracle.
5. Independently verifies 84 cases and freezes expected hashes.
6. Runs the 12 translator fixtures and captures canonical TPR-IR/GRL/result.
7. Builds and starts the current Go engine on port 8081.
8. Boots Laravel through the same `TypedPayrollRuleIrService` application boundary and runs all differential requests.
9. Runs the full Go suite, Go vet, and full Laravel suite.
10. Regenerates metrics, root-cause/translator/final reports, and `EXPERIMENT_MANIFEST.json`.
11. Exits non-zero on migration, seed, oracle verification, translator, differential mismatch, suite, vet, or report failure.

The test engine process started by the script is stopped in a `finally` block.

## Determinism checks

The manifest records commits, baseline tag, versions, seed, UTC timestamp, testing database, and SHA-256 hashes. The stable core hashes to compare are:

- `oracle_input_cases.json`
- `oracle_expected_results.json`
- `actual_results.json`
- `differential_results.csv`
- `mismatch_details.json`

Expected-result verification is deliberately performed before the engine starts. The runner rechecks all freeze hashes and refuses to continue on drift.

## Interpreting failure

- Oracle verifier failure: expected results are not frozen; adjudicate without consulting production output.
- Differential exit 1: inspect `mismatch_details.json` and preserve the case.
- Port error: stop the unrelated process or configure the environment before rerunning.
- Database guard error: create/use the dedicated `_testing` database; never weaken the guard.
