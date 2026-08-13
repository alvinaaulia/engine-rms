#!/usr/bin/env bash
set -Eeuo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENGINE_REPO="$(cd "$PACKAGE_DIR/.." && pwd)"
if [[ -z "${LARAVEL_REPO:-}" ]]; then
  LARAVEL_REPO="$(cd "$ENGINE_REPO/../papa-website-public" && pwd)"
fi
ENGINE_REF="${ENGINE_REF:-HEAD}"
LARAVEL_REF="${LARAVEL_REF:-HEAD}"
RUN_ID="wsl-clean-$(date -u +%Y%m%dT%H%M%SZ)"
TEMP_ROOT="$(mktemp -d /tmp/engine-rms-clean.XXXXXX)"
TEMP_LOGS="$TEMP_ROOT/raw-logs"
SNAP_ROOT="$TEMP_ROOT/artifact"
SNAP_ENGINE="$SNAP_ROOT/engine-rms"
SNAP_LARAVEL="$SNAP_ROOT/papa-website-public"
SNAP_PACKAGE="$SNAP_ENGINE/differential_validation"
SNAP_CLEAN="$SNAP_PACKAGE/runs/clean-environment"
FINAL_RUN_DIR="$PACKAGE_DIR/runs/clean-environment/$RUN_ID"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
START_SECONDS="$(date +%s)"
VALIDATION_EXIT=0
FINALIZE_EXIT=0
FAILURE_STAGE="VALIDATION_RUNNER"
FAILURE_REASON=""
PRIMARY_LOG="raw-logs/validation-runner.log"

cleanup() {
  if [[ "${KEEP_WSL_SNAPSHOT:-0}" != "1" && -n "$TEMP_ROOT" && "$TEMP_ROOT" == /tmp/engine-rms-clean.* ]]; then
    chmod -R u+w "$TEMP_ROOT" 2>/dev/null || true
    rm -rf -- "$TEMP_ROOT"
  fi
}
trap cleanup EXIT

require() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing WSL dependency: $1" >&2
    exit 2
  }
}

for tool in composer curl git go jq make mysql mysqladmin php python3; do require "$tool"; done
php -r 'foreach (["bcmath", "curl", "dom", "gd", "mbstring", "pdo_mysql", "zip"] as $extension) { if (!extension_loaded($extension)) { fwrite(STDERR, "Missing PHP extension: {$extension}\n"); exit(2); } }'
[[ "$(uname -s)" == "Linux" ]] || { echo "This runner must execute inside WSL/Linux" >&2; exit 2; }
for variable in DB_HOST DB_DATABASE DB_USERNAME; do
  [[ -n "${!variable:-}" ]] || { echo "Missing required environment variable: $variable" >&2; exit 2; }
done
[[ "$DB_DATABASE" == *test* ]] || {
  echo "Refusing database without test marker: $DB_DATABASE" >&2
  exit 2
}

mkdir -p "$TEMP_LOGS" "$SNAP_ROOT"
set +e
{
  git clone --no-hardlinks --no-checkout "$ENGINE_REPO" "$SNAP_ENGINE"
  git -C "$SNAP_ENGINE" checkout --detach "$ENGINE_REF"
  git clone --no-hardlinks --no-checkout "$LARAVEL_REPO" "$SNAP_LARAVEL"
  git -C "$SNAP_LARAVEL" checkout --detach "$LARAVEL_REF"
  printf 'engine_ref=%s\nengine_commit=%s\nengine_status=%s\n' \
    "$ENGINE_REF" "$(git -C "$SNAP_ENGINE" rev-parse HEAD)" "$(git -C "$SNAP_ENGINE" status --porcelain)"
  printf 'laravel_ref=%s\nlaravel_commit=%s\nlaravel_status=%s\n' \
    "$LARAVEL_REF" "$(git -C "$SNAP_LARAVEL" rev-parse HEAD)" "$(git -C "$SNAP_LARAVEL" status --porcelain)"
} >"$TEMP_LOGS/source-identity.log" 2>&1
SNAPSHOT_EXIT=$?
set -e

if [[ "$SNAPSHOT_EXIT" -ne 0 ]]; then
  echo "WSL source snapshot failed; see $TEMP_LOGS/source-identity.log" >&2
  exit "$SNAPSHOT_EXIT"
fi

rm -rf -- "$SNAP_PACKAGE/runs"
mkdir -p "$SNAP_CLEAN/raw-logs"

set +e
(
  set -Eeuo pipefail
  python3 -m venv "$TEMP_ROOT/venv"
  # shellcheck disable=SC1091
  source "$TEMP_ROOT/venv/bin/activate"
  python -m pip install --disable-pip-version-check --no-cache-dir -r "$SNAP_PACKAGE/requirements.txt"
  export COMPOSER_CACHE_DIR="$TEMP_ROOT/composer-cache"
  export COMPOSER_MAX_PARALLEL_HTTP="2"
  export COMPOSER_PROCESS_TIMEOUT="1800"
  composer --no-cache install --working-dir="$SNAP_LARAVEL" --no-interaction --prefer-dist --no-progress
  export GOMODCACHE="$TEMP_ROOT/go-mod-cache"
  export GOCACHE="$TEMP_ROOT/go-build-cache"
  go -C "$SNAP_ENGINE" mod download
  cp "$SNAP_LARAVEL/.env.example" "$SNAP_LARAVEL/.env"
  DB_HOST="$DB_HOST" DB_PORT="${DB_PORT:-3306}" DB_DATABASE="$DB_DATABASE" \
    DB_USERNAME="$DB_USERNAME" DB_PASSWORD="${DB_PASSWORD:-}" \
    php "$SNAP_LARAVEL/artisan" key:generate --force
) >"$TEMP_LOGS/dependency-install.log" 2>&1
PREPARATION_EXIT=$?
set -e

if [[ "$PREPARATION_EXIT" -ne 0 ]]; then
  VALIDATION_EXIT="$PREPARATION_EXIT"
  FAILURE_STAGE="ENVIRONMENT_PREPARATION"
  FAILURE_REASON="native WSL dependency installation failed"
  PRIMARY_LOG="raw-logs/dependency-install.log"
else
  set +e
  (
    set -Eeuo pipefail
    export MYSQL_PWD="${DB_PASSWORD:-}"
    mysqladmin --protocol=tcp --host="$DB_HOST" --port="${DB_PORT:-3306}" --user="$DB_USERNAME" ping
    mysql --protocol=tcp --host="$DB_HOST" --port="${DB_PORT:-3306}" --user="$DB_USERNAME" \
      --database="$DB_DATABASE" --batch --skip-column-names \
      --execute='SELECT DATABASE(), @@collation_server, @@time_zone'
    DB_CONNECTION=mysql DB_HOST="$DB_HOST" DB_PORT="${DB_PORT:-3306}" DB_DATABASE="$DB_DATABASE" \
      DB_USERNAME="$DB_USERNAME" DB_PASSWORD="${DB_PASSWORD:-}" APP_ENV=testing \
      php "$SNAP_LARAVEL/artisan" about --only=environment
    source "$TEMP_ROOT/venv/bin/activate"
    python - "$SNAP_PACKAGE" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
frozen = json.loads((root / "FROZEN_ARTIFACT_MANIFEST.json").read_text(encoding="utf-8"))
for filename, key in (
    ("reference_policy.json", "policy_sha256"),
    ("oracle_input_cases.json", "corpus_sha256"),
    ("oracle_expected_results.json", "expected_results_sha256"),
):
    actual = hashlib.sha256((root / filename).read_bytes()).hexdigest()
    if actual != frozen[key]:
        raise SystemExit(f"frozen hash mismatch: {filename}")
    print(f"{filename}={actual}")
PY
    printf 'php='; php -r 'echo PHP_VERSION, PHP_EOL;'
    printf 'composer='; composer --version --no-ansi
    printf 'mysql_client='; mysql --version
    printf 'go='; go version
    printf 'python='; python --version
    printf 'os='; grep '^PRETTY_NAME=' /etc/os-release
    printf 'kernel='; uname -srvm
    printf 'timezone='; date +%Z
    printf 'locale='; locale | grep '^LC_ALL='
  ) >"$TEMP_LOGS/service-health.log" 2>&1
  READINESS_EXIT=$?
  set -e

  if [[ "$READINESS_EXIT" -ne 0 ]]; then
    VALIDATION_EXIT="$READINESS_EXIT"
    FAILURE_STAGE="SERVICE_READINESS"
    FAILURE_REASON="WSL database, Laravel, or frozen-artifact readiness failed"
    PRIMARY_LOG="raw-logs/service-health.log"
  else
    set +e
    (
      set -Eeuo pipefail
      source "$TEMP_ROOT/venv/bin/activate"
      export ENGINE_DIR="$SNAP_ENGINE" LARAVEL_DIR="$SNAP_LARAVEL" RUNS_DIR="$SNAP_PACKAGE/runs"
      export SOURCE_SNAPSHOT_VERIFIED=1 CLEAN_OUTPUTS=1 USE_EXTERNAL_FIXED_ENGINE=0 ALLOW_DIRTY=0
      export DB_CONNECTION=mysql DB_HOST="$DB_HOST" DB_PORT="${DB_PORT:-3306}" DB_DATABASE="$DB_DATABASE"
      export DB_USERNAME="$DB_USERNAME" DB_PASSWORD="${DB_PASSWORD:-}"
      export RULE_ENGINE_URL="http://127.0.0.1:8081" TZ="${TZ:-Asia/Jakarta}" LC_ALL="${LC_ALL:-C.UTF-8}"
      export COMPOSER_CACHE_DIR="$TEMP_ROOT/composer-cache" GOMODCACHE="$TEMP_ROOT/go-mod-cache" GOCACHE="$TEMP_ROOT/go-build-cache"
      bash "$SNAP_PACKAGE/run_all.sh"
    ) >"$TEMP_LOGS/validation-runner.log" 2>&1
    VALIDATION_EXIT=$?
    set -e
    if [[ "$VALIDATION_EXIT" -ne 0 ]]; then
      FAILURE_REASON="WSL validation runner exited non-zero; see raw-logs/validation-runner.log"
    fi
  fi
fi

mkdir -p "$SNAP_CLEAN/raw-logs"
cp "$TEMP_LOGS"/* "$SNAP_CLEAN/raw-logs/" 2>/dev/null || true
FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DURATION="$(( $(date +%s) - START_SECONDS ))"
set +e
"$TEMP_ROOT/venv/bin/python" "$SNAP_PACKAGE/finalize_clean_run.py" \
  --exit-code "$VALIDATION_EXIT" --started-at "$STARTED_AT" --finished-at "$FINISHED_AT" \
  --duration-seconds "$DURATION" --run-id "$RUN_ID" --runner-type WSL_NATIVE \
  --failure-stage "$FAILURE_STAGE" --failure-reason "$FAILURE_REASON" --primary-log "$PRIMARY_LOG" \
  --runner-id "$(hostname)" --runner-os "$(grep '^PRETTY_NAME=' /etc/os-release | cut -d= -f2- | tr -d '\"') WSL2 $(uname -r)" \
  --runner-architecture "$(uname -m)"
FINALIZE_EXIT=$?
set -e

mkdir -p "$FINAL_RUN_DIR"
cp -a "$SNAP_CLEAN/." "$FINAL_RUN_DIR/"
printf '{"run_id":"%s","validation_exit":%s,"finalize_exit":%s,"evidence":"%s"}\n' \
  "$RUN_ID" "$VALIDATION_EXIT" "$FINALIZE_EXIT" "$FINAL_RUN_DIR"

if [[ "$VALIDATION_EXIT" -ne 0 ]]; then
  exit "$VALIDATION_EXIT"
fi
exit "$FINALIZE_EXIT"
