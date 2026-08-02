# Evidence integrity notice

This is a genuine failed WSL-native clean-run attempt. Source snapshot,
environment preparation, service readiness, migration, both reconstructed
baseline runs, fixed differential, translator fixtures, Go tests, Go vet, and the
dedicated full-pipeline E2E test all executed before the full Laravel suite failed.

The full Laravel suite reported:

- `CompanyTaxOperationalStatusUnitTest`: a business date was compared as a
  timezone-sensitive timestamp, producing `SCHEDULED` instead of `ACTIVE`;
- `OvertimeApprovalWorkflowTest`: the WSL PHP environment lacked the GD extension
  required by `UploadedFile::fake()->image()`.

- Final status: `FAIL`
- Failure stage: `VALIDATION_RUNNER`
- Failed command exit code: `2`
- Full Laravel result: 153 passed, 2 failed, 2 deprecated (1580 assertions)
- Primary evidence: `raw-logs/hardening--laravel-tests-hardening.stdout.log`
- Source commit used: `455aabbeb3ae206b6f8fb9d433fbb4e67927b5e2`
- Temporal replay: `NOT_STARTED`

Later report/schema-generation commands were not executed. No partial result is
upgraded to PASS. The subsequent remediation makes the date comparison use the
business `Y-m-d`, supplies an explicit `asOf` in the regression test, and declares
GD as a required PHP extension.
