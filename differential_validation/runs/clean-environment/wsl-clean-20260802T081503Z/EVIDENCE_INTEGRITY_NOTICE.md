# Evidence integrity notice

This is a genuine failed WSL-native clean-run attempt. Environment preparation and
service readiness passed, including all three frozen hashes. The validation wrapper
then returned exit code 2 before any recorded experiment command because the outer
runner accepted database name `website_papa_v2_wsl_clean`, while `run_all.sh`
requires a name containing `test`.

- Final status: `FAIL`
- Failure stage: `VALIDATION_RUNNER`
- Service readiness: `PASS`
- Experiment stages: `NOT_EXECUTED`
- Source commit used: `13969d232d276d069dd235f5c65fae1e06e6ae18`
- Temporal replay: `NOT_STARTED`

The raw wrapper logs are missing from this failed run because `run_all.sh` cleared
the snapshot `runs/` directory before the outer runner copied its temporary logs.
That evidence-copy defect is itself part of this attempt's limitation; no log or
PASS status has been reconstructed. The next source revision recreates the
run-scoped raw-log directory after validation and aligns both database guards.
