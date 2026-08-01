
# Differential validation final report V3

## 1. Executive verdict
Local evidence remains internally consistent, but clean-environment reproduction was not executed. Readiness is A.

## 2. Frozen source and artifact baseline
Source commits, tags, snapshots, and artifact SHA-256 values are frozen in `FROZEN_ARTIFACT_MANIFEST.json`.

## 3. Clean-environment specification
The specification uses four services: app-laravel, mysql, rule-engine-go, and validation-runner. Primary command: `make clean-validate`.

## 4. Clean-environment execution result
Clean-environment reproduction remains NOT_EXECUTED because neither Docker nor an external clean CI runner with access to the private Laravel source was available during the audit.

## 5-10. Evaluation results
| Evaluation layer | Independent cases | Assertion layer | Mismatch | Result | Evidence |
|---|---|---|---|---|---|
| Reconstructed baseline | 624 | none | 8 | LOCAL_RECONSTRUCTED_EVIDENCE; CLEAN_NOT_EXECUTED | runs/reconstructed-baseline/manifest.json |
| Fixed differential | 624 | none | 0 | LOCAL_PASS; CLEAN_NOT_EXECUTED | runs/fixed/mismatch_details.json |
| Translator fixture | 12 | none | 0 | LOCAL_PASS; CLEAN_NOT_EXECUTED | runs/hardening/raw-logs/translator-hardening.meta.json |
| Full payroll pipeline | 32 | persistence asserted on same transactions | 0 | LOCAL_PASS; CLEAN_NOT_EXECUTED | e2e-execution-traces.json |
| Configuration guard | 4 | pre-execution rejection | 0 | LOCAL_PASS; CLEAN_NOT_EXECUTED | CONFIGURATION_GUARD_REPORT.md |

The 32 persistence evaluations are assertions on the same 32 full-pipeline transactions, not additional independent cases. The 4 guards are pre-execution rejections, not payroll transactions.

Definitions: a translator fixture tests TPR-to-GRL translation in isolation; Laravel-to-Go integration crosses the HTTP boundary; full payroll pipeline covers database facts through Go/GRULE and persistence; persistence assertion checks the salary record created by that same transaction; configuration guard rejects invalid configuration before Go execution.

## 11. Oracle verification breakdown
89 independently verified, 535 policy-derived, and 0 adjudicated.

## 12. Metric observability
Measured metrics retain value and denominator. Unobservable metrics remain null with reasons in `metric-results.json`.

## 13. Reproducibility evidence
Preflight commands, unavailable-runner attempts, pinned intended image digests, and null clean-run results are under `runs/clean-environment/`. No local result is relabeled clean evidence.

## 14. Domain validation status
`NOT_AUTHORITATIVE_BUSINESS_ORACLE / DOMAIN_VALIDATION_PENDING`.

## 15. Claims supported
The local reconstructed baseline repeated its mismatch set; local fixed, translator, pipeline, persistence, and guard evaluations passed against the frozen reference artifacts.

## 16. Claims not supported
No fresh-run equivalence, third-party rerun, authoritative payroll correctness, legal compliance, or completed domain approval is claimed.

## 17. Limitations
No Docker daemon, installed Linux distribution, usable GitHub CLI, or valid non-interactive credential for the private Laravel repository was available. Go internal TPR/GRL steps are source-verified but not separately runtime-instrumented by request ID.

## 18. Temporal replay gate
Temporal replay remains `NOT_STARTED` and is blocked until a clean runner completes with final exit code zero and all frozen hashes match.

## 19. Readiness decision
A - Clean environment could not be prepared.
