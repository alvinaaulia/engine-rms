# Evidence integrity notice

This attempt genuinely failed at `SERVICE_READINESS` because the Laravel image lacked `ext-zip`; the raw Docker, service, Laravel, Go, and MySQL logs are valid evidence of that failure.

The non-wrapper PASS entries in `command-results.json` are inherited tracked metadata from before this attempt. Their timestamps precede this run and they are **not clean-run evidence**. The attempt did not start the validation runner, reconstructed baseline, fixed differential, translator, Laravel test suite, E2E pipeline, guards, schema validation, or report generation.

The orchestration was corrected after this attempt to clear the complete snapshot `runs/` tree before build and to classify post-readiness stages as `NOT_EXECUTED` when readiness fails. This notice preserves the original derived file while preventing its inherited entries from being misinterpreted.
