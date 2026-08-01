# Service readiness report

| Service | Required readiness | Observed status | Evidence |
|---|---|---|---|
| MySQL | fresh database, connection, migrations | NOT_EXECUTED | runs/clean-environment/runner-audit-20260801T112156Z/manifest.json |
| Laravel | testing boot and database connection | NOT_EXECUTED | runs/clean-environment/runner-audit-20260801T112156Z/manifest.json |
| Go | health endpoint and engine readiness | NOT_EXECUTED | runs/clean-environment/runner-audit-20260801T112156Z/manifest.json |
| Validation runner | frozen artifacts and matching hashes | FROZEN INPUT HASHES PASS; RUNNER NOT_EXECUTED | CLEAN_HASH_VERIFICATION_REPORT.json |
