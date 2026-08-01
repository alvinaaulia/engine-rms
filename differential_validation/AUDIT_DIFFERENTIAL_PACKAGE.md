
# Audit differential package

| File/area | Function | Input | Output | Confirmed problem | Remediation |
|---|---|---|---|---|---|
| `generate_corpus.py` | Corpus generator | Frozen policy/seed | cases JSON/CSV | Categories were index/modulo labels | Treatment predicates, route, rationale, and validator |
| `verify_oracle.py` | Independent verifier | Expected/corpus/policy | Frozen expected/status report | Unverified rows called adjudicated | Independent and policy-derived statuses |
| `run_differential.py` | Runtime runner/comparator | Frozen cases/expected | Actual/CSV/mismatch | Single canonical route and overwritten output | Real canonical/legacy routes and run directories |
| `generate_reports.py` | Report generator | Raw artifacts/logs | Research reports | Static counts/status/durations | Strict evidence parsers and refusal on bad evidence |
| `runs/` | Experimental evidence | Baseline/fixed engines | Separate runs | Baseline/fixed mixed; initial raw overwritten | Explicit reconstructed baseline and fixed evidence |
| `metrics.json` | Observability model | Comparator output | Metric status/value | Unmeasured fields reported as zero | Measured/not-observable/not-applicable states |
| Laravel E2E test | Full pipeline | Isolated DB + live Go | JUnit/E2E JSON | Full payroll service path absent | 36-case DB/service/HTTP/GRULE/persistence subset |
| schemas/validator | Artifact gate | All JSON artifacts | validation report | Weak cross-artifact validation | JSON Schema plus IDs/hashes/metric/adjudication checks |
| reproducibility files | External rerun | source/env | logs/manifests/reports | Local Windows paths and binary reliance | Relative Bash/Make path with source builds |

Historical reports containing the invalid terminology remain replaced, not used as evidence. The user-owned `differential_validation.zip` was not modified.
