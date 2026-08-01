# Clean-run raw logs

Only runner-availability command logs exist for this audit. `docker-build.log`, migration/test/differential/E2E/schema/report logs do not exist because no clean environment was executed. Empty placeholders are intentionally not created. A future successful `make clean-validate` run writes those execution logs and replaces the `NOT_EXECUTED` manifest through `finalize_clean_run.py`.
