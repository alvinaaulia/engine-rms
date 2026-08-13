#!/usr/bin/env bash
set -Eeuo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENGINE_DIR="${ENGINE_DIR:-$(cd "$PACKAGE_DIR/.." && pwd)}"
LARAVEL_DIR="${LARAVEL_DIR:-$(cd "$ENGINE_DIR/../papa-website-public" && pwd)}"
RUN_ID="${RUN_ID:-temporal-clean-$(date -u +%Y%m%dT%H%M%SZ)}"
RUN_DIR="$PACKAGE_DIR/runs/temporal-replay/$RUN_ID"
RAW="$RUN_DIR/raw-logs"
TMP_DIR="$(mktemp -d)"
ENGINE_PID=""
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cleanup() {
  if [[ -n "$ENGINE_PID" ]] && kill -0 "$ENGINE_PID" 2>/dev/null; then
    kill "$ENGINE_PID" 2>/dev/null || true
    wait "$ENGINE_PID" 2>/dev/null || true
  fi
  [[ -n "$TMP_DIR" && "$TMP_DIR" == */tmp.* ]] && rm -rf -- "$TMP_DIR"
}
trap cleanup EXIT

for tool in curl git go php python; do
  command -v "$tool" >/dev/null 2>&1 || { echo "Missing dependency: $tool" >&2; exit 2; }
done
[[ -f "$LARAVEL_DIR/artisan" ]] || { echo "Laravel repository not found: $LARAVEL_DIR" >&2; exit 2; }
export APP_ENV=testing DB_CONNECTION=mysql DB_DATABASE="${DB_DATABASE:-website_papa_v2_testing}"
export RULE_ENGINE_URL="${RULE_ENGINE_URL:-http://127.0.0.1:8081}" TZ="${TZ:-Asia/Bangkok}"
[[ "${DB_DATABASE,,}" == *test* ]] || { echo "Refusing non-test database: $DB_DATABASE" >&2; exit 2; }
[[ -z "$(git -C "$ENGINE_DIR" status --porcelain)" ]] || { echo "Engine repository must be clean" >&2; exit 2; }
[[ -z "$(git -C "$LARAVEL_DIR" status --porcelain)" ]] || { echo "Laravel repository must be clean" >&2; exit 2; }

mkdir -p "$RAW" "$RUN_DIR/legacy-regression"
python - "$ENGINE_DIR" "$LARAVEL_DIR" "$RUN_ID" "$STARTED_AT" >"$RUN_DIR/source-identity.json" <<'PY'
import json, subprocess, sys
engine, laravel, run_id, started = sys.argv[1:]
def git(repo, *args): return subprocess.check_output(["git", "-C", repo, *args], text=True).strip()
print(json.dumps({
  "run_id": run_id, "started_at": started,
  "engine_commit": git(engine, "rev-parse", "HEAD"), "engine_branch": git(engine, "branch", "--show-current"),
  "laravel_commit": git(laravel, "rev-parse", "HEAD"), "laravel_branch": git(laravel, "branch", "--show-current"),
  "engine_dirty_before_run": False, "laravel_dirty_before_run": False,
}, indent=2))
PY

run_step() {
  local name="$1" cwd="$2"; shift 2
  local stdout="$RAW/$name.stdout.log" stderr="$RAW/$name.stderr.log" exit_file="$RAW/$name.exit-code.txt"
  set +e
  (cd "$cwd" && "$@") >"$stdout" 2>"$stderr"
  local code=$?
  set -e
  printf '%s\n' "$code" >"$exit_file"
  if [[ "$code" -ne 0 ]]; then
    echo "FAILED: $name (exit $code)" >&2
    tail -80 "$stderr" >&2 || true
    tail -80 "$stdout" >&2 || true
    exit "$code"
  fi
}

wait_engine() {
  for _ in $(seq 1 90); do
    curl --fail --silent "$RULE_ENGINE_URL/health" >/dev/null 2>&1 && return 0
    sleep 1
  done
  echo "Engine health timeout: $RULE_ENGINE_URL" >&2
  exit 2
}

suffix=""
[[ "${OS:-}" == "Windows_NT" || "$(uname -s)" == MINGW* ]] && suffix=".exe"

run_step migration "$LARAVEL_DIR" php artisan migrate:fresh --force --no-ansi
run_step environment-laravel "$LARAVEL_DIR" php artisan about --only=environment --no-ansi
run_step environment-database "$LARAVEL_DIR" php -r 'require "vendor/autoload.php"; $app=require "bootstrap/app.php"; $app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap(); $row=Illuminate\Support\Facades\DB::selectOne("SELECT VERSION() AS version, DATABASE() AS database_name, @@collation_server AS collation_name, @@time_zone AS server_timezone"); echo json_encode($row, JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES), PHP_EOL;'
run_step environment-go "$ENGINE_DIR" go version
run_step environment-python "$ENGINE_DIR" python --version
run_step go-tests "$ENGINE_DIR" go test -count=1 ./...
run_step go-vet "$ENGINE_DIR" go vet ./...

go -C "$ENGINE_DIR" build -tags differential_baseline -o "$TMP_DIR/baseline$suffix" .
for repeat in 1 2; do
  "$TMP_DIR/baseline$suffix" >"$RAW/baseline-$repeat-engine.stdout.log" 2>"$RAW/baseline-$repeat-engine.stderr.log" & ENGINE_PID=$!
  wait_engine
  run_step "baseline-$repeat-differential" "$ENGINE_DIR" python differential_validation/differential_runner/run_differential.py \
    --output-dir "differential_validation/runs/temporal-replay/$RUN_ID/legacy-regression/reconstructed-baseline-repeat-$repeat" \
    --run-id "temporal-baseline-repeat-$repeat" --allow-mismatches
  kill "$ENGINE_PID"; wait "$ENGINE_PID" 2>/dev/null || true; ENGINE_PID=""
done

go -C "$ENGINE_DIR" build -o "$TMP_DIR/fixed$suffix" .
"$TMP_DIR/fixed$suffix" >"$RAW/fixed-engine.stdout.log" 2>"$RAW/fixed-engine.stderr.log" & ENGINE_PID=$!
wait_engine
run_step fixed-differential "$ENGINE_DIR" python differential_validation/differential_runner/run_differential.py \
  --output-dir "differential_validation/runs/temporal-replay/$RUN_ID/legacy-regression/fixed" --run-id temporal-fixed
run_step translator-fixtures "$ENGINE_DIR" go test -count=1 -run TestTranslationValidationFixtures .

export FULL_PIPELINE_E2E_OUTPUT="$RUN_DIR/full-pipeline-e2e.json"
run_step laravel-full-suite "$LARAVEL_DIR" php artisan test --log-junit "$RAW/laravel-full-suite.junit.xml"
run_step migration-before-temporal "$LARAVEL_DIR" php artisan migrate:fresh --force --no-ansi
run_step temporal-experiment "$LARAVEL_DIR" php artisan temporal-replay:experiment --output="$RUN_DIR" --repeat=2 --no-ansi
run_step temporal-finalize "$PACKAGE_DIR" python finalize_temporal_run.py --run-dir "$RUN_DIR" --started-at "$STARTED_AT"

echo "Temporal clean reproduction PASS: $RUN_DIR"
