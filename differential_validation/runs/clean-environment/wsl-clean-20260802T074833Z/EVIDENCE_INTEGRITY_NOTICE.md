# Evidence integrity notice

This is a genuine failed WSL-native clean-run attempt. Environment preparation
completed, but service readiness stopped before any experiment command because
`oracle_input_cases.json` used LF bytes in the Linux snapshot while the frozen
manifest recorded the semantically identical CRLF artifact produced on Windows.

- Final status: `FAIL`
- Failure stage: `SERVICE_READINESS`
- Experiment stages: `NOT_EXECUTED`
- Primary evidence: `raw-logs/service-health.log`
- Source commit used: `aa9f742754dd35014f5959e16f960372822d57fa`
- Temporal replay: `NOT_STARTED`

No prior local PASS artifact was copied into this run. The subsequent source fix
canonicalizes the existing frozen JSON byte representation; it does not alter the
corpus cases, reference policy, or expected payroll values.
