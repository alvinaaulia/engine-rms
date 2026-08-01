
# Differential validation final report V2

## Executive verdict

The fixed implementation agrees with the frozen reference oracle across 624 differential cases. The reconstructed pre-remediation behavior reproducibly yields 8 mismatches. Evidence hardening is locally verified, but clean-environment reproduction is `NOT_EXECUTED` and domain validation is pending.

## Evaluation layers

| Evaluation layer | Cases | Measured unit | Mismatch | Result | Evidence |
|---|---|---|---|---|---|
| Reconstructed baseline differential | 624 | corpus case | 8 | RECONSTRUCTED_MISMATCH_REPRODUCED | runs/reconstructed-baseline/manifest.json |
| Fixed differential | 624 | corpus case | 0 | PASS | runs/fixed/mismatch_details.json |
| Translator fixtures | 12 | translator fixture | 0 | PASS | runs/hardening/raw-logs/translator-hardening.meta.json |
| Laravel-to-Go / full payroll pipeline | 32 | payroll transaction | 0 | PASS | e2e-execution-traces.json |
| Persistence E2E | 32 | persisted payroll transaction | 0 | PASS | e2e-execution-traces.json |
| Laravel configuration guards | 4 | rejected configuration | 0 | PASS | e2e-execution-traces.json |

## Claims supported

- Fixed/reference exact agreement for the measured differential cases.
- A clearly labeled reconstructed baseline reproduced the stable mismatch set in 2 executions.
- Independently verified and policy-derived oracle cases are separated per case.
- Translator, full payroll pipeline, persistence, and Laravel-only configuration guards are reported separately.

## Claims not supported

- No original historical baseline raw output is claimed.
- The reference oracle is not authoritative HRD, organizational, legal, or statutory evidence.
- Clean-container reproduction is not claimed as PASS.
- The 4 pre-HTTP configuration guards are not called full-payroll pipeline executions.

## Reconstructed evidence

`runs/reconstructed-baseline/` contains the method, source state, remediation patch, two runs, stable semantic hashes, and limitations.

## Original evidence

Current fixed raw logs, source hashes, corpus, frozen expected results, policy, test logs, and per-case E2E traces are retained. The unavailable historical raw baseline is explicitly excluded.

## Unobservable metrics

See `metric-results.json`; unobservable values are null with reasons and no false zero.

## Domain validity limitation

Oracle breakdown: 89 independently verified, 535 policy-derived, and 0 adjudicated. Status remains `NOT_AUTHORITATIVE_BUSINESS_ORACLE / DOMAIN_VALIDATION_PENDING`.

## Reproducibility status

Local source/test/evidence regeneration is available. Clean-environment status is `NOT_EXECUTED` because docker, docker compose.

## Next-stage gate

Do not begin temporal replay until the provided clean Docker/CI command completes successfully and its logs/digests are added. Temporal replay status is `NOT_STARTED`.

## Readiness

Decision D - not ready because clean-environment reproduction was not executed successfully.
