# Temporal Replay Source Baseline

## Verification timestamp

Source verification was performed on 2026-08-02 in the `Asia/Bangkok` host timezone. Git identities below were obtained with `git rev-parse` and `git rev-list`; they are not copied assumptions.

## Repository identity

| Repository role | Path | Starting tag resolution | Branch creation base | New branch | Pre-branch dirty status |
|---|---|---|---|---|---|
| Laravel application | `C:/PROJECT/papa-website-v2` | `tpr-ir-clean-closure-v4` -> `269c6a656804c9ef11078539d65850f93a23f577` | `269c6a656804c9ef11078539d65850f93a23f577` | `feature/temporal-payroll-replay-v1` | clean |
| Go engine and validation package | `C:/PROJECT/engine-rms` | `tpr-ir-clean-closure-v4` -> `069581549fadaa8f74281722592c5bfa68ae4053` | `6a374633a25fb08e2541e7fa1c096e3895db023e` | `feature/temporal-payroll-replay-v1` | clean |
| Validation package | `C:/PROJECT/engine-rms/differential_validation` | same Git repository and source tag as engine | same as engine | same as engine | clean |

The requested path `C:/PROJECT/differential_validation` does not exist. The canonical package is the tracked directory inside `engine-rms`; creating a second copy would introduce ambiguous evidence identity.

The engine branch base is the V4 evidence closure commit. Its source-code ancestor is the required engine tag commit; commits between the tag and branch base only preserve failed/successful WSL evidence and V4 reporting. Frozen V4 files and the existing `runs/clean-environment/wsl-clean-20260802T090158Z` run are immutable inputs to this work.

## Database and migration state

| Field | Observed value |
|---|---|
| Server | MySQL 8.0.30 |
| Application schema | `papa_website_v2` |
| Schema collation | `utf8mb4_0900_ai_ci` |
| Server timezone | `SYSTEM` |
| Applied migration rows | 72 |
| Highest batch | 2 |
| Last migration by batch/name | `2026_07_12_000003_add_descriptions_to_system_rate_key_catalog` |

`php artisan migrate:status --env=testing` did not return within the observation window. Migration state above was therefore read directly from the application schema's `migrations` table through the MySQL client. No migration was executed during source freeze.

## Starting reproduction status

The frozen V4 clean WSL run remains `PASS`: reconstructed baseline 624/8 twice, fixed differential 624/0, translator 12/0, full payroll pipeline 32/0, four configuration guards accepted, Laravel 157 tests with 1587 assertions and no failures/errors/skips, Go tests PASS, and Go vet PASS. Temporal replay remains `NOT_STARTED` at this baseline.

