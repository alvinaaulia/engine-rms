#!/usr/bin/env bash
set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_DIR="${ENGINE_DIR:-$(cd "$PACKAGE_DIR/.." && pwd)}"
LARAVEL_DIR="${LARAVEL_DIR:-$(cd "$ENGINE_DIR/../papa-website-v2" && pwd)}"
RUNS_DIR="${RUNS_DIR:-$PACKAGE_DIR/runs}"
LOG_DIR="$RUNS_DIR/fixed/logs"
TMP_DIR="$(mktemp -d)"
ENGINE_PID=""

cleanup() {
  if [[ -n "$ENGINE_PID" ]] && kill -0 "$ENGINE_PID" 2>/dev/null; then kill "$ENGINE_PID"; fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

for repo in "$ENGINE_DIR" "$LARAVEL_DIR"; do
  git -C "$repo" rev-parse HEAD
  if [[ -n "$(git -C "$repo" status --porcelain)" && "${ALLOW_DIRTY:-0}" != "1" ]]; then
    echo "Refusing dirty repository: $repo (set ALLOW_DIRTY=1 only for exploratory runs)" >&2
    exit 2
  fi
done

mkdir -p "$LOG_DIR" "$RUNS_DIR/baseline/logs"
python -m pip install -r "$PACKAGE_DIR/requirements.txt"

export APP_ENV=testing DB_CONNECTION=mysql DB_DATABASE="${DB_DATABASE:-website_papa_v2_testing}"
export RULE_ENGINE_URL="${RULE_ENGINE_URL:-http://127.0.0.1:8081}"
export LARAVEL_ROOT="$LARAVEL_DIR"
export TZ="${TZ:-Asia/Bangkok}" LC_ALL="${LC_ALL:-C.UTF-8}"
if [[ "$DB_DATABASE" != *test* ]]; then echo "Refusing non-test database: $DB_DATABASE" >&2; exit 2; fi

python "$PACKAGE_DIR/record_command.py" --name migration --output-dir "$LOG_DIR" --cwd "$LARAVEL_DIR" -- php artisan migrate:fresh --env=testing --force
python "$PACKAGE_DIR/record_command.py" --name corpus-generation --output-dir "$LOG_DIR" --cwd "$ENGINE_DIR" -- python differential_validation/generate_corpus.py
python "$PACKAGE_DIR/record_command.py" --name oracle-generation --output-dir "$LOG_DIR" --cwd "$ENGINE_DIR" -- python differential_validation/oracle_calculator/reference_oracle.py
python "$PACKAGE_DIR/record_command.py" --name oracle-verification --output-dir "$LOG_DIR" --cwd "$ENGINE_DIR" -- python differential_validation/oracle_calculator/verify_oracle.py

suffix=""; [[ "${OS:-}" == "Windows_NT" || "$(uname -s)" == MINGW* ]] && suffix=".exe"
go build -tags differential_baseline -o "$TMP_DIR/baseline$suffix" "$ENGINE_DIR"
"$TMP_DIR/baseline$suffix" >"$RUNS_DIR/baseline/logs/engine.stdout.log" 2>"$RUNS_DIR/baseline/logs/engine.stderr.log" & ENGINE_PID=$!
sleep 2
python "$PACKAGE_DIR/record_command.py" --name differential --output-dir "$RUNS_DIR/baseline/logs" --cwd "$ENGINE_DIR" -- python differential_validation/differential_runner/run_differential.py --output-dir differential_validation/runs/baseline --run-id reconstructed-baseline --allow-mismatches
kill "$ENGINE_PID"; wait "$ENGINE_PID" 2>/dev/null || true; ENGINE_PID=""

go build -o "$TMP_DIR/fixed$suffix" "$ENGINE_DIR"
"$TMP_DIR/fixed$suffix" >"$RUNS_DIR/fixed/logs/engine.stdout.log" 2>"$RUNS_DIR/fixed/logs/engine.stderr.log" & ENGINE_PID=$!
sleep 2
python "$PACKAGE_DIR/record_command.py" --name differential --output-dir "$LOG_DIR" --cwd "$ENGINE_DIR" -- python differential_validation/differential_runner/run_differential.py --output-dir differential_validation/runs/fixed --run-id fixed
python "$PACKAGE_DIR/record_command.py" --name translator-go-test --output-dir "$LOG_DIR" --cwd "$ENGINE_DIR" -- go test -json -run TestTranslationValidationFixtures -count=1 .
python "$PACKAGE_DIR/record_command.py" --name go-tests --output-dir "$LOG_DIR" --cwd "$ENGINE_DIR" -- go test -json ./... -count=1
python "$PACKAGE_DIR/record_command.py" --name go-vet --output-dir "$LOG_DIR" --cwd "$ENGINE_DIR" -- go vet ./...

export FULL_PIPELINE_E2E_OUTPUT="$RUNS_DIR/fixed/full_pipeline_e2e.json"
python "$PACKAGE_DIR/record_command.py" --name laravel-tests --output-dir "$LOG_DIR" --cwd "$LARAVEL_DIR" --evidence-file laravel-tests.xml -- php artisan test --log-junit "$LOG_DIR/laravel-tests.xml"
python "$PACKAGE_DIR/record_command.py" --name e2e --output-dir "$LOG_DIR" --cwd "$LARAVEL_DIR" --evidence-file e2e-junit.xml -- php artisan test tests/Feature/DifferentialFullPipelineE2ETest.php --log-junit "$LOG_DIR/e2e-junit.xml"

python "$PACKAGE_DIR/generate_run_evidence.py"
python "$PACKAGE_DIR/validate_artifacts.py"
python -m unittest differential_validation.tests.test_evidence
python "$PACKAGE_DIR/generate_reports.py"

