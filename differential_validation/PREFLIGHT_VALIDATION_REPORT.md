# Preflight Validation Report

## Status

Preflight is complete. Rounding and hit-policy decisions were frozen before corpus generation, the baseline was committed and tagged in both repositories, active data was audited, and all initially known suite failures were resolved.

## Frozen baseline

| Repository | Baseline commit | Annotated tag |
|---|---|---|
| Laravel `papa-website-v2` | `ca16f0500d8404cecaca03950cfc252072ca3e23` | `tpr-ir-differential-baseline-v1` |
| Go `engine-rms` | `1dcad9df1be852263590fd23ab11ce569ea1c99e` | `tpr-ir-differential-baseline-v1` |

Both annotated tags were peeled and verified to point to the listed commits.

## Toolchain

| Tool | Version at preflight |
|---|---|
| PHP | 8.4.20 |
| Laravel | 10.50.2 |
| MySQL client/server | 8.0.30 / 8.0.30 |
| Go | 1.26.2 windows/amd64 |
| GRULE | v1.20.4 |
| OS | Windows 10 Pro 10.0.19045, 64-bit |

## Preflight suites

- Laravel: 155 tests, 835 assertions, PASS (114.81 s) after the non-payroll fixes.
- Go: `go test ./... -count=1`, PASS.
- Go static analysis: `go vet ./...`, PASS.

The final suite results after differential fixes are recorded in the final report and reproducibility run.

## Initial Laravel failures resolved

1. Auth group/role scoping fixture now creates and supplies the required project/team relation.
2. Authentication redirect assertions now follow intended role destinations.
3. Tax approval workflow assertion now follows the expired-status message.
4. Director leave listing now supplies the `role` view variable, fixing a real HTTP 500.
5. Payroll-rate schema-column cache can be flushed and is reset per test, removing order leakage.

## Frozen business decisions

| Decision | Frozen value |
|---|---|
| Calculation scale | 6 decimals |
| Comparator scale | 6 decimals |
| Reporting scale | 2 decimals |
| Rounding | HALF_UP |
| Rounding points | candidate amount, COLLECT_SUM aggregate, summary |
| COLLECT_SUM representation | one aggregate component with contributor provenance |
| FIRST ordering | priority descending, then stable rule ID ascending |
| Hit policy storage | inferred by Laravel adapter; canonical policy is explicit in TPR-IR payload |

These decisions are also machine-readable in `reference_policy.json`.

## Active-data audit

Audit date: 2026-08-01. The database contained 11 active rule versions (`1`, `3`–`12`), 10 active component codes, and the rate configuration reflected in `reference_policy.json`.

| Check | Finding | Disposition |
|---|---|---|
| SET and ADD on same target | None; active rules are ADD | PASS |
| PRIORITY tie | Not applicable to active ADD set | PASS |
| Duplicate rule ID | None | PASS |
| Duplicate action | None | PASS |
| Invalid effective date | None | PASS |
| Unknown field | `employee.annual_bonus_eligible` and `employee.thr_eligible` were initially absent from static catalogs | FIXED in Laravel and Go with regression coverage |
| Period overlap | Three ADD performance rules overlap in period but conditions are mutually exclusive and COLLECT_SUM-compatible | ACCEPTED |

No active company-tax configuration was present. The active `TAX_FLAT` rule and explicit synthetic rate variations are therefore treated as the testable tax surface.

## Oracle authority warning

Active rule records cite `perhitungan_manual_penggajian_hrd_per_aturan.xlsx`, but that workbook was not found in either repository. The experiment therefore uses a **reference oracle**, not an authoritative HRD oracle.
