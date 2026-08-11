#!/usr/bin/env bash
set -Eeuo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENGINE_REPO="$(cd "$PACKAGE_DIR/.." && pwd)"
LARAVEL_REPO="${LARAVEL_REPO:-$(cd "$ENGINE_REPO/../papa-website-v2" && pwd)}"
ENGINE_REF="${ENGINE_REF:-0dc6c0032484285fce37001b80323cd4c1afd86c}"
LARAVEL_REF="${LARAVEL_REF:-45b82783056a4277f32517667ab519a104550e7c}"
BRANCH="feature/temporal-replay-evidence-closure-v2"
TEMP_ROOT="$(mktemp -d /tmp/temporal-v2-wsl.XXXXXX)"
SNAP_ENGINE="$TEMP_ROOT/engine-rms"
SNAP_LARAVEL="$TEMP_ROOT/papa-website-v2"
FINAL_PARENT="$PACKAGE_DIR/runs/temporal-replay-v2"

cleanup() {
  if [[ "${KEEP_WSL_SNAPSHOT:-0}" != "1" && -n "$TEMP_ROOT" && "$TEMP_ROOT" == /tmp/temporal-v2-wsl.* ]]; then
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

for tool in composer curl git go mysql mysqladmin php python3; do
  require "$tool"
done

php -r 'foreach (["bcmath", "curl", "dom", "gd", "mbstring", "pdo_mysql", "zip"] as $extension) { if (!extension_loaded($extension)) { fwrite(STDERR, "Missing PHP extension: {$extension}\n"); exit(2); } }'
[[ "$(uname -s)" == "Linux" ]] || { echo "This runner must execute inside WSL/Linux" >&2; exit 2; }
for variable in DB_HOST DB_DATABASE DB_USERNAME; do
  [[ -n "${!variable:-}" ]] || { echo "Missing required environment variable: $variable" >&2; exit 2; }
done
[[ "$DB_DATABASE" == *test* ]] || { echo "Refusing non-test database: $DB_DATABASE" >&2; exit 2; }

echo "Preparing clean WSL source snapshots..."
git -c safe.directory="$ENGINE_REPO" -c safe.directory="$ENGINE_REPO/.git" \
  clone --no-hardlinks --no-checkout "$ENGINE_REPO" "$SNAP_ENGINE"
git -C "$SNAP_ENGINE" checkout -B "$BRANCH" "$ENGINE_REF"
git -c safe.directory="$LARAVEL_REPO" -c safe.directory="$LARAVEL_REPO/.git" \
  clone --no-hardlinks --no-checkout "$LARAVEL_REPO" "$SNAP_LARAVEL"
git -C "$SNAP_LARAVEL" checkout -B "$BRANCH" "$LARAVEL_REF"

[[ "$(git -C "$SNAP_ENGINE" rev-parse HEAD)" == "$ENGINE_REF" ]] || { echo "Engine source identity mismatch" >&2; exit 2; }
[[ "$(git -C "$SNAP_LARAVEL" rev-parse HEAD)" == "$LARAVEL_REF" ]] || { echo "Laravel source identity mismatch" >&2; exit 2; }
[[ -z "$(git -C "$SNAP_ENGINE" status --porcelain)" ]] || { echo "Engine snapshot is dirty" >&2; exit 2; }
[[ -z "$(git -C "$SNAP_LARAVEL" status --porcelain)" ]] || { echo "Laravel snapshot is dirty" >&2; exit 2; }

echo "Installing locked dependencies..."
python3 -m venv "$TEMP_ROOT/venv"
# shellcheck disable=SC1091
source "$TEMP_ROOT/venv/bin/activate"
python -m pip install --disable-pip-version-check -r "$SNAP_ENGINE/differential_validation/requirements.txt"
COMPOSER_ALLOW_SUPERUSER=1 composer install --working-dir="$SNAP_LARAVEL" --no-interaction --prefer-dist --no-progress
go -C "$SNAP_ENGINE" mod download
cp "$SNAP_LARAVEL/.env.example" "$SNAP_LARAVEL/.env"
DB_CONNECTION=mysql DB_HOST="$DB_HOST" DB_PORT="${DB_PORT:-3306}" DB_DATABASE="$DB_DATABASE" \
  DB_USERNAME="$DB_USERNAME" DB_PASSWORD="${DB_PASSWORD:-}" APP_ENV=testing \
  php "$SNAP_LARAVEL/artisan" key:generate --force --no-ansi
# Composer's package-discovery hook rewrites these tracked caches even when the
# lockfile is unchanged. Restore the exact committed caches before source freeze.
git -C "$SNAP_LARAVEL" checkout -- bootstrap/cache/packages.php bootstrap/cache/services.php
[[ -z "$(git -C "$SNAP_LARAVEL" status --porcelain)" ]] || {
  echo "Laravel snapshot changed during dependency preparation" >&2
  git -C "$SNAP_LARAVEL" status --short >&2
  exit 2
}

export DB_CONNECTION=mysql DB_HOST DB_PORT="${DB_PORT:-3306}" DB_DATABASE DB_USERNAME DB_PASSWORD="${DB_PASSWORD:-}"
export APP_ENV=testing RULE_ENGINE_URL="http://127.0.0.1:8081" TZ="${TZ:-Asia/Jakarta}" LC_ALL="${LC_ALL:-C.UTF-8}"

echo "Checking the dedicated testing database..."
export MYSQL_PWD="${DB_PASSWORD:-}"
mysqladmin --protocol=tcp --host="$DB_HOST" --port="$DB_PORT" --user="$DB_USERNAME" ping
mysql --protocol=tcp --host="$DB_HOST" --port="$DB_PORT" --user="$DB_USERNAME" \
  --database="$DB_DATABASE" --batch --skip-column-names \
  --execute='SELECT DATABASE(), @@collation_server, @@time_zone'

echo "Running Temporal Replay Evidence Closure v2 in WSL..."
bash "$SNAP_ENGINE/differential_validation/scripts/clean_temporal_v2.sh"

mapfile -t generated_runs < <(find "$SNAP_ENGINE/differential_validation/runs/temporal-replay-v2" -mindepth 1 -maxdepth 1 -type d -name 'temporal-v2-*' -print)
[[ "${#generated_runs[@]}" -eq 1 ]] || { echo "Expected exactly one generated Temporal v2 run" >&2; exit 2; }
generated_run="${generated_runs[0]}"
run_id="$(basename "$generated_run")"
final_run="$FINAL_PARENT/$run_id"
[[ ! -e "$final_run" ]] || { echo "Refusing to overwrite existing run: $final_run" >&2; exit 2; }

mkdir -p "$FINAL_PARENT"
cp -a "$generated_run" "$final_run"
printf '{"status":"PASS","runner":"WSL_NATIVE_NO_DOCKER","run_id":"%s","run_dir":"%s","engine_commit":"%s","laravel_commit":"%s"}\n' \
  "$run_id" "$final_run" "$ENGINE_REF" "$LARAVEL_REF"
