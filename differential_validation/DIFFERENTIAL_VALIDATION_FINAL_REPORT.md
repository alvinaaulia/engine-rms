
# Differential validation final report

## Executive result

The reconstructed baseline found 8 mismatches; the fixed run found 0 across 624 cases. This establishes remediation against the frozen reference policy, while domain authority remains unvalidated.

## Evidence breakdown

| Evidence | Cases/fixtures | Mismatch/failure | Result |
|---|---|---|---|
| Baseline differential | 624 | 8 | FAIL |
| Fixed differential | 624 | 0 | PASS |
| Translator fixtures | 12 | 0 | PASS |
| Full-pipeline E2E | 36 | 0 | PASS |

Oracle cases: 89 independently verified and 535 policy-derived; no unsupported adjudication. Unobservable metrics remain null rather than zero. Full test evidence is recorded in `AUTOMATED_EVIDENCE_GENERATION_REPORT.md`.

## Limitations

- The pre-remediation raw baseline was overwritten; the preserved evidence is a clearly labeled reconstruction.
- The reference oracle is not an authoritative HRD/company/legal oracle.
- Raw amount, rounding decision point, rate version, and tax version are not observable through the production API.
- Clean-environment Docker execution must be reported from actual execution; absence of Docker on the current host cannot be converted into a success claim.
- Temporal replay was intentionally not started.
