# Evidence integrity notice

This is a genuine failed WSL-native clean-run attempt. Environment preparation
completed, but service readiness stopped before any experiment command because a
global `core.autocrlf=true` snapshot setting converted `reference_policy.json` to
CRLF. Its frozen byte representation is LF, while the corpus and expected-result
artifacts are frozen as CRLF.

- Final status: `FAIL`
- Failure stage: `SERVICE_READINESS`
- Experiment stages: `NOT_EXECUTED`
- Primary evidence: `raw-logs/service-health.log`
- Source commit used: `624d466bbe8ea223dc93184d7300d05ee78ddfb0`
- Temporal replay: `NOT_STARTED`

No prior local PASS artifact was copied into this run. The subsequent source fix
declares the per-file line-ending rules in `.gitattributes`; it does not alter the
reference policy, corpus cases, or expected payroll values.
