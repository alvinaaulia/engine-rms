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

- Go 1.25.6 (the version declared by `go.mod`)
- PHP 8.1 or newer and Composer dependencies for Laravel
- Python 3.14 with `requirements.txt`
- WSL 2 with Ubuntu and Make, or Docker Compose
- isolated MySQL database whose name contains `test` or `testing`

Copy `.env.example`, set credentials for the isolated testing database, and install Laravel dependencies with `composer install`. The deterministic corpus seed, timezone, locale, dependency version, and container image digests are committed.

## Primary command on WSL 2

Install the native Linux prerequisites once:

```bash
sudo apt-get -o Acquire::ForceIPv4=true update
sudo apt-get install -y make jq unzip ca-certificates curl php-cli php-mysql \
  php-mbstring php-xml php-curl php-zip php-bcmath php-gd composer \
  python3-pip python3-venv default-mysql-client
```

Install the exact Go toolchain declared by `go.mod` from the official Go archive and
verify the published SHA-256 before extraction. Then, from Ubuntu WSL 2, provide a
dedicated empty testing database without printing its password:

```bash
cd /mnt/c/PROJECT/engine-rms/differential_validation
export DB_HOST="$(ip route show default | awk '{print $3; exit}')"
export DB_PORT=3306
export DB_DATABASE=website_papa_v2_wsl_clean_testing
export DB_USERNAME=tpr_ir_wsl
read -rsp 'Testing DB password: ' DB_PASSWORD; echo
export DB_PASSWORD
make clean-validate-wsl
```

`clean-validate-wsl` clones both tagged repositories into a new directory on the
Linux filesystem, creates new Python, Composer, Go module, and Go build cache
directories, installs from lockfiles, verifies the frozen hashes, checks MySQL and
Laravel readiness, runs the complete validation workflow, and copies only the
run-scoped evidence back to `runs/clean-environment/<run-id>/`. It never uses the
Windows Laravel `vendor` directory or a precompiled Windows Go binary. Any failed
dependency, readiness check, mismatch, test, schema, or report returns non-zero.

The MySQL schema must be dedicated to this audit. `migrate:fresh` is the first
recorded experiment command, so tables from an application or previous run are not
accepted as starting evidence.

After a successful run, validate that complete evidence set and regenerate the V4
closure reports from it:

```bash
make finalize-v4-wsl RUN_ID=wsl-clean-YYYYMMDDTHHMMSSZ
```

This finalization command refuses a non-PASS manifest, a failed recorded command,
changed frozen hash, unstable reconstructed baseline, fixed mismatch, incomplete
translator/pipeline/guard evidence, or failed JUnit/Go evidence.

## Optional Docker route

```bash
docker compose build --no-cache
docker compose run --rm validation-runner
```

The PHP, Python, Go, Composer, and MySQL image references use registry digests. Use
this route only on a machine that can sustain Docker Desktop. Docker and WSL runs
have separate run identifiers and runner metadata; a WSL run never claims image
digests or container IDs.

## Review bundle

After committing the final source, assemble Git-tracked source without vendor/build output:

```bash
make package
```

The output contains both source repositories and the differential package. Private dependencies and company policy sources remain subject to `LICENSE-or-ACCESS-NOTE.md`.

## Interpretation

The baseline is `RECONSTRUCTED_BASELINE`, because the original raw eight-mismatch file had previously been overwritten. The fixed result demonstrates equality with a frozen reference policy. It does not establish an authoritative, HRD-validated, company-accurate, or legally compliant payroll policy.
