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
make clean-validate
```

The command builds containers without cache, starts MySQL, the Laravel application, and the fixed Go service, then runs the validation container. It refuses a dirty tree, verifies repository commits and frozen hashes, guards the test database name, prepares migrations, builds the reconstructed engine from source, executes both baseline repeats and the fixed comparison, runs translator fixtures, Go and Laravel tests, Go vet, E2E traces, schemas, manifests, and reports. An unresolved mismatch or failed command returns non-zero.

The PowerShell file is only a convenience wrapper around the same Bash route.

## Optional clean container route

```bash
docker compose build --no-cache
docker compose run --rm validation-runner
```

The PHP, Python, Go, Composer, and MySQL image references use registry digests. Docker, WSL Linux, and usable external-CI credentials were unavailable on the audit host, so this route is supplied but its clean-environment result is `NOT_EXECUTED`, not success.

## Review bundle

After committing the final source, assemble Git-tracked source without vendor/build output:

```bash
make package
```

The output contains both source repositories and the differential package. Private dependencies and company policy sources remain subject to `LICENSE-or-ACCESS-NOTE.md`.

## Interpretation

The baseline is `RECONSTRUCTED_BASELINE`, because the original raw eight-mismatch file had previously been overwritten. The fixed result demonstrates equality with a frozen reference policy. It does not establish an authoritative, HRD-validated, company-accurate, or legally compliant payroll policy.
