#!/usr/bin/env bash
set -Eeuo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENGINE_DIR="${ENGINE_DIR:-$(cd "$PACKAGE_DIR/.." && pwd)}"
LARAVEL_DIR="${LARAVEL_DIR:-$(cd "$ENGINE_DIR/../papa-website-public" && pwd)}"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_STAMP="$(date -u -d "$STARTED_AT" +%Y%m%dT%H%M%SZ)"
ENGINE_COMMIT="$(git -C "$ENGINE_DIR" rev-parse HEAD)"
LARAVEL_COMMIT="$(git -C "$LARAVEL_DIR" rev-parse HEAD)"
SHORT_HASH="$(python -c 'import hashlib,sys; print(hashlib.sha256("|".join(sys.argv[1:]).encode()).hexdigest()[:8])' "$STARTED_AT" "$ENGINE_COMMIT" "$LARAVEL_COMMIT")"
RUN_ID="temporal-v2-${RUN_STAMP}-${SHORT_HASH}"
RUN_DIR="$PACKAGE_DIR/runs/temporal-replay-v2/$RUN_ID"
RAW="$RUN_DIR/raw-logs"
V1_OUTPUT="$RUN_DIR/temporal-v1-regression"
TMP_DIR="$(mktemp -d)"
ENGINE_PID=""

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
[[ -z "$(git -C "$ENGINE_DIR" status --porcelain)" ]] || { echo "Engine repository must be clean" >&2; exit 2; }
[[ -z "$(git -C "$LARAVEL_DIR" status --porcelain)" ]] || { echo "Laravel repository must be clean" >&2; exit 2; }

export APP_ENV=testing DB_CONNECTION=mysql DB_DATABASE="${DB_DATABASE:-website_papa_v2_testing}"
export RULE_ENGINE_URL="${RULE_ENGINE_URL:-http://127.0.0.1:8081}" TZ="${TZ:-Asia/Bangkok}"
export TEMPORAL_RESEARCH_TRACE=true
[[ "${DB_DATABASE,,}" == *test* ]] || { echo "Refusing non-test database: $DB_DATABASE" >&2; exit 2; }

mkdir -p "$RAW" "$RUN_DIR/legacy-regression" "$V1_OUTPUT/raw-logs"
python - "$ENGINE_DIR" "$LARAVEL_DIR" "$RUN_ID" "$STARTED_AT" >"$RUN_DIR/source-identity.json" <<'PY'
import json, subprocess, sys
engine, laravel, run_id, started = sys.argv[1:]
def git(repo, *args): return subprocess.check_output(["git", "-C", repo, *args], text=True).strip()
print(json.dumps({
  "artifact_version": "2.0", "run_id": run_id, "started_at": started,
  "engine_commit": git(engine, "rev-parse", "HEAD"), "validation_commit": git(engine, "rev-parse", "HEAD"),
  "engine_branch": git(engine, "branch", "--show-current"),
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
    tail -100 "$stderr" >&2 || true
    tail -100 "$stdout" >&2 || true
    exit "$code"
  fi
}

wait_engine() {
  for _ in $(seq 1 90); do
    curl --fail --silent "$RULE_ENGINE_URL/health" >/dev/null 2>&1 && return 0
    sleep 1
  done
  echo "Engine health timeout: $RULE_ENGINE_URL" >&2
  return 2
}

start_engine() {
  local name="$1" binary="$2"
  "$binary" >"$RAW/$name-engine.stdout.log" 2>"$RAW/$name-engine.stderr.log" & ENGINE_PID=$!
  local code=0
  wait_engine || code=$?
  printf '%s\n' "$code" >"$RAW/$name-engine-health.exit-code.txt"
  if [[ "$code" -ne 0 ]]; then
    echo "FAILED: $name engine health (exit $code)" >&2
    exit "$code"
  fi
}

suffix=""
[[ "${OS:-}" == "Windows_NT" || "$(uname -s)" == MINGW* ]] && suffix=".exe"

run_step migration "$LARAVEL_DIR" php artisan migrate:fresh --force --no-ansi
run_step environment-database "$LARAVEL_DIR" php -r 'require "vendor/autoload.php"; $app=require "bootstrap/app.php"; $app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap(); $row=Illuminate\Support\Facades\DB::selectOne("SELECT VERSION() AS version, DATABASE() AS database_name, @@collation_server AS collation_name, @@time_zone AS server_timezone"); echo json_encode($row, JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES), PHP_EOL;'
run_step environment-capture "$PACKAGE_DIR" python capture_temporal_v2_environment.py "$RUN_DIR" "$RAW/environment-database.stdout.log"
run_step go-tests "$ENGINE_DIR" go test -count=1 ./...
run_step go-vet "$ENGINE_DIR" go vet ./...

run_step build-baseline "$ENGINE_DIR" go build -tags differential_baseline -o "$TMP_DIR/baseline$suffix" .
for repeat in 1 2; do
  start_engine "baseline-$repeat" "$TMP_DIR/baseline$suffix"
  run_step "baseline-$repeat-differential" "$ENGINE_DIR" python differential_validation/differential_runner/run_differential.py \
    --output-dir "differential_validation/runs/temporal-replay-v2/$RUN_ID/legacy-regression/reconstructed-baseline-repeat-$repeat" \
    --run-id "temporal-v2-baseline-repeat-$repeat" --allow-mismatches
  kill "$ENGINE_PID"; wait "$ENGINE_PID" 2>/dev/null || true; ENGINE_PID=""
done

run_step build-fixed "$ENGINE_DIR" go build -o "$TMP_DIR/fixed$suffix" .
start_engine fixed "$TMP_DIR/fixed$suffix"
run_step fixed-differential "$ENGINE_DIR" python differential_validation/differential_runner/run_differential.py \
  --output-dir "differential_validation/runs/temporal-replay-v2/$RUN_ID/legacy-regression/fixed" --run-id temporal-v2-fixed
run_step translator-fixtures "$ENGINE_DIR" go test -count=1 -run TestTranslationValidationFixtures .

export FULL_PIPELINE_E2E_OUTPUT="$RUN_DIR/full-pipeline-e2e.json"
run_step laravel-full-suite "$LARAVEL_DIR" php artisan test --log-junit "$RAW/laravel-full-suite.junit.xml"
run_step migration-before-temporal "$LARAVEL_DIR" php artisan migrate:fresh --force --no-ansi
run_step temporal-v1-regression "$LARAVEL_DIR" php artisan temporal-replay:experiment --output="$V1_OUTPUT" --repeat=2 --no-ansi
run_step temporal-v2-collector "$LARAVEL_DIR" php artisan temporal-replay:evidence-v2 \
  --output="$RUN_DIR" --v1-output="$V1_OUTPUT" --run-id="$RUN_ID" --started-at="$STARTED_AT" --repeat=2 --no-ansi
run_step temporal-v2-finalize "$PACKAGE_DIR" python finalize_temporal_v2.py --run-dir "$RUN_DIR"

echo "Temporal Replay Evidence Closure v2 PASS: $RUN_DIR"
