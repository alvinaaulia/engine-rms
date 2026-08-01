#!/usr/bin/env bash
set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMP_LOGS="$(mktemp -d)"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
START_SECONDS="$(date +%s)"

cleanup() {
  docker compose -f "$PACKAGE_DIR/docker-compose.yml" rm -sf validation-runner app-laravel rule-engine-go mysql >/dev/null 2>&1 || true
  rm -rf "$TEMP_LOGS"
}
trap cleanup EXIT

cd "$PACKAGE_DIR"
docker compose build --no-cache >"$TEMP_LOGS/docker-build.log" 2>&1
docker compose up -d --wait mysql app-laravel rule-engine-go >"$TEMP_LOGS/service-start.log" 2>&1

set +e
docker compose run --name differential-clean-validation validation-runner >"$TEMP_LOGS/validation-runner.log" 2>&1
VALIDATION_EXIT=$?
set -e

docker compose logs --no-color mysql >"$TEMP_LOGS/mysql.log" 2>&1 || true
docker compose logs --no-color app-laravel >"$TEMP_LOGS/app-laravel.log" 2>&1 || true
docker compose logs --no-color rule-engine-go >"$TEMP_LOGS/rule-engine-go.log" 2>&1 || true
docker compose images -q | sort -u | while read -r image_id; do
  [[ -n "$image_id" ]] && docker image inspect "$image_id" --format '{{json .}}'
done >"$TEMP_LOGS/images.json"
CONTAINER_ID="$(docker inspect --format '{{.Id}}' differential-clean-validation 2>/dev/null || true)"

mkdir -p "$PACKAGE_DIR/runs/clean-environment/raw-logs"
cp "$TEMP_LOGS"/*.log "$PACKAGE_DIR/runs/clean-environment/raw-logs/"
cp "$TEMP_LOGS/images.json" "$PACKAGE_DIR/runs/clean-environment/raw-logs/docker-images.json"
FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DURATION="$(( $(date +%s) - START_SECONDS ))"

python "$PACKAGE_DIR/finalize_clean_run.py" \
  --exit-code "$VALIDATION_EXIT" --started-at "$STARTED_AT" --finished-at "$FINISHED_AT" \
  --duration-seconds "$DURATION" --container-id "$CONTAINER_ID"
exit "$VALIDATION_EXIT"
