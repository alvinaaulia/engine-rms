#!/usr/bin/env bash
set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_DIR="${ENGINE_DIR:-$(cd "$PACKAGE_DIR/.." && pwd)}"
LARAVEL_DIR="${LARAVEL_DIR:-$(cd "$ENGINE_DIR/../papa-website-v2" && pwd)}"
RUNS_DIR="${RUNS_DIR:-$PACKAGE_DIR/runs}"
HARD_LOGS="$RUNS_DIR/hardening/raw-logs"
TMP_DIR="$(mktemp -d)"
ENGINE_PID=""

cleanup() {
  if [[ -n "$ENGINE_PID" ]] && kill -0 "$ENGINE_PID" 2>/dev/null; then
    kill "$ENGINE_PID"
    wait "$ENGINE_PID" 2>/dev/null || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

require() { command -v "$1" >/dev/null 2>&1 || { echo "Missing dependency: $1" >&2; exit 2; }; }
for tool in git go php python; do require "$tool"; done
[[ -f "$LARAVEL_DIR/artisan" ]] || { echo "Laravel repository not found: $LARAVEL_DIR" >&2; exit 2; }

for repo in "$ENGINE_DIR" "$LARAVEL_DIR"; do
  git -C "$repo" rev-parse HEAD
  if [[ -n "$(git -C "$repo" status --porcelain)" && "${ALLOW_DIRTY:-0}" != "1" && "${SOURCE_SNAPSHOT_VERIFIED:-0}" != "1" ]]; then
    echo "Refusing dirty repository: $repo" >&2
    exit 2
  fi
done

if [[ "${CLEAN_OUTPUTS:-0}" == "1" ]]; then
  expected_runs="$(realpath -m "$PACKAGE_DIR/runs")"
  requested_runs="$(realpath -m "$RUNS_DIR")"
  if [[ "$requested_runs" != "$expected_runs" ]]; then
    echo "Refusing to clear unexpected runs directory: $requested_runs" >&2
    exit 2
  fi
  rm -rf -- "$requested_runs"
fi

mkdir -p "$HARD_LOGS" "$RUNS_DIR/fixed/raw-logs"
for repeat in 1 2; do mkdir -p "$RUNS_DIR/reconstructed-baseline/repeat-$repeat/raw-logs"; done
python -m pip install -r "$PACKAGE_DIR/requirements.txt"

export APP_ENV=testing DB_CONNECTION=mysql DB_DATABASE="${DB_DATABASE:-website_papa_v2_testing}"
FIXED_RULE_ENGINE_URL="${RULE_ENGINE_URL:-http://127.0.0.1:8081}"
export RULE_ENGINE_URL="http://127.0.0.1:8081"
export LARAVEL_ROOT="$LARAVEL_DIR" TZ="${TZ:-Asia/Bangkok}" LC_ALL="${LC_ALL:-C.UTF-8}"
[[ "$DB_DATABASE" == *test* ]] || { echo "Refusing non-test database: $DB_DATABASE" >&2; exit 2; }

record() { python "$PACKAGE_DIR/record_command.py" "$@"; }
record --name migration --output-dir "$HARD_LOGS" --cwd "$LARAVEL_DIR" -- php artisan migrate:fresh --env=testing --force
record --name corpus-generation --output-dir "$HARD_LOGS" --cwd "$ENGINE_DIR" -- python differential_validation/generate_corpus.py
record --name oracle-generation --output-dir "$HARD_LOGS" --cwd "$ENGINE_DIR" -- python differential_validation/oracle_calculator/reference_oracle.py
record --name oracle-verification --output-dir "$HARD_LOGS" --cwd "$ENGINE_DIR" -- python differential_validation/oracle_calculator/verify_oracle.py

suffix=""; [[ "${OS:-}" == "Windows_NT" || "$(uname -s)" == MINGW* ]] && suffix=".exe"
go -C "$ENGINE_DIR" build -tags differential_baseline -o "$TMP_DIR/baseline$suffix" .
for repeat in 1 2; do
  repeat_dir="$RUNS_DIR/reconstructed-baseline/repeat-$repeat"
  "$TMP_DIR/baseline$suffix" >"$repeat_dir/raw-logs/engine.stdout.log" 2>"$repeat_dir/raw-logs/engine.stderr.log" & ENGINE_PID=$!
  sleep 2
  record --name differential --output-dir "$repeat_dir/raw-logs" --cwd "$ENGINE_DIR" -- python differential_validation/differential_runner/run_differential.py --output-dir "differential_validation/runs/reconstructed-baseline/repeat-$repeat" --run-id "reconstructed-baseline-repeat-$repeat" --allow-mismatches
  kill "$ENGINE_PID"; wait "$ENGINE_PID" 2>/dev/null || true; ENGINE_PID=""
done
mkdir -p "$RUNS_DIR/baseline"
cp "$RUNS_DIR/reconstructed-baseline/repeat-2/actual_results.json" "$RUNS_DIR/baseline/actual_results.json"
cp "$RUNS_DIR/reconstructed-baseline/repeat-2/mismatch_details.json" "$RUNS_DIR/baseline/mismatch_details.json"
cp "$RUNS_DIR/reconstructed-baseline/repeat-2/differential_results.csv" "$RUNS_DIR/baseline/differential_results.csv"

export RULE_ENGINE_URL="$FIXED_RULE_ENGINE_URL"
if [[ "${USE_EXTERNAL_FIXED_ENGINE:-0}" != "1" ]]; then
  go -C "$ENGINE_DIR" build -o "$TMP_DIR/fixed$suffix" .
  "$TMP_DIR/fixed$suffix" >"$RUNS_DIR/fixed/raw-logs/engine.stdout.log" 2>"$RUNS_DIR/fixed/raw-logs/engine.stderr.log" & ENGINE_PID=$!
  sleep 2
fi
record --name differential-hardening --output-dir "$RUNS_DIR/fixed/raw-logs" --cwd "$ENGINE_DIR" -- python differential_validation/differential_runner/run_differential.py --output-dir differential_validation/runs/fixed --run-id fixed-hardening
record --name translator-hardening --output-dir "$HARD_LOGS" --cwd "$ENGINE_DIR" -- go test -json -run TestTranslationValidationFixtures -count=1 .
record --name go-tests-hardening --output-dir "$HARD_LOGS" --cwd "$ENGINE_DIR" -- go test -json ./... -count=1
record --name go-vet-hardening --output-dir "$HARD_LOGS" --cwd "$ENGINE_DIR" -- go vet ./...

export FULL_PIPELINE_E2E_OUTPUT="$RUNS_DIR/fixed/full_pipeline_e2e.json"
record --name e2e-hardening --output-dir "$RUNS_DIR/fixed/raw-logs" --cwd "$LARAVEL_DIR" --evidence-file e2e-hardening-junit.xml -- php artisan test tests/Feature/DifferentialFullPipelineE2ETest.php --log-junit "$RUNS_DIR/fixed/raw-logs/e2e-hardening-junit.xml"
record --name laravel-tests-hardening --output-dir "$HARD_LOGS" --cwd "$LARAVEL_DIR" --evidence-file laravel-tests-hardening.xml -- php artisan test --log-junit "$HARD_LOGS/laravel-tests-hardening.xml"

record --name run-evidence-generation --output-dir "$HARD_LOGS" --cwd "$ENGINE_DIR" -- python differential_validation/generate_run_evidence.py
record --name hardening-artifact-generation --output-dir "$HARD_LOGS" --cwd "$ENGINE_DIR" -- python differential_validation/generate_hardening_artifacts.py
record --name schema-validation --output-dir "$HARD_LOGS" --cwd "$ENGINE_DIR" -- python differential_validation/validate_artifacts.py
record --name validator-tests --output-dir "$HARD_LOGS" --cwd "$ENGINE_DIR" -- python -m unittest differential_validation.tests.test_evidence differential_validation.tests.test_artifact_validator
record --name report-generation --output-dir "$HARD_LOGS" --cwd "$ENGINE_DIR" -- python differential_validation/generate_reports.py
record --name final-schema-validation --output-dir "$HARD_LOGS" --cwd "$ENGINE_DIR" -- python differential_validation/validate_artifacts.py
