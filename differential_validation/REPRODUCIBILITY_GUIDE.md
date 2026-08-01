# Reproducibility guide

## Layout

Place both repositories as siblings:

```text
artifact/
├── papa-website-v2/
└── engine-rms/
    └── differential_validation/
```

Do not use the precompiled Windows binary as experimental evidence. The runner builds both reconstructed-baseline and fixed services from source.

## Prerequisites

- Go 1.26.2
- PHP 8.4 and Composer dependencies for Laravel
- Python 3.14 with `requirements.txt`
- Git Bash and Make, or Docker Compose
- isolated MySQL database whose name contains `test` or `testing`

Copy `.env.example`, set credentials for the isolated testing database, and install Laravel dependencies with `composer install`. The deterministic corpus seed, timezone, locale, dependency version, and container image digests are committed.

## Primary command

From `engine-rms/differential_validation` in Git Bash:

```bash
make validate-differential
```

The command refuses a dirty tree by default, verifies repository commits, guards the test database name, prepares migrations, creates and verifies the frozen oracle, builds baseline and fixed engines from source, runs both differential comparisons, runs translator fixtures, full Go tests, Go vet, the full Laravel suite, the true E2E subset, schema validation, evidence-parser tests, manifests, and reports. An unresolved fixed mismatch or failed command returns non-zero.

The PowerShell file is only a convenience wrapper around the same Bash route.

## Optional clean container route

```bash
docker compose run --rm differential-validation
```

The Go, Composer, and MySQL image references use registry digests. Docker was unavailable on the remediation host, so this route is supplied but its clean-environment result is `NOT_EXECUTED`, not success.

## Review bundle

After committing the final source, assemble Git-tracked source without vendor/build output:

```bash
make package
```

The output contains both source repositories and the differential package. Private dependencies and company policy sources remain subject to `LICENSE-or-ACCESS-NOTE.md`.

## Interpretation

The baseline is `RECONSTRUCTED_BASELINE`, because the original raw eight-mismatch file had previously been overwritten. The fixed result demonstrates equality with a frozen reference policy. It does not establish an authoritative, HRD-validated, company-accurate, or legally compliant payroll policy.
