#!/usr/bin/env bash
set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENGINE_REPO="$(cd "$PACKAGE_DIR/.." && pwd)"
LARAVEL_REPO="$(cd "$ENGINE_REPO/../papa-website-v2" && pwd)"
ENGINE_REF="${ENGINE_REF:-tpr-ir-clean-closure-v4}"
LARAVEL_REF="${LARAVEL_REF:-tpr-ir-clean-closure-v4}"
RUN_ID="clean-$(date -u +%Y%m%dT%H%M%SZ)"
PROJECT_NAME="differential-${RUN_ID,,}"
TEMP_ROOT="$(mktemp -d)"
TEMP_LOGS="$TEMP_ROOT/raw-logs"
ARTIFACT_ROOT="$TEMP_ROOT/artifact"
SNAP_ENGINE="$ARTIFACT_ROOT/engine-rms"
SNAP_LARAVEL="$ARTIFACT_ROOT/papa-website-v2"
SNAP_PACKAGE="$SNAP_ENGINE/differential_validation"
SNAP_CLEAN="$SNAP_PACKAGE/runs/clean-environment"
FINAL_RUN_DIR="$PACKAGE_DIR/runs/clean-environment/$RUN_ID"
OVERRIDE_FILE="$TEMP_ROOT/docker-compose.override.yml"
COMPOSE_FILE=""
CONTAINER_NAME="${PROJECT_NAME}-validation-runner"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
START_SECONDS="$(date +%s)"

mkdir -p "$TEMP_LOGS" "$ARTIFACT_ROOT"

cleanup() {
  if [[ -n "$COMPOSE_FILE" ]]; then
    docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" -f "$OVERRIDE_FILE" down -v --remove-orphans >/dev/null 2>&1 || true
  fi
  if [[ "$SNAP_ENGINE" == "$TEMP_ROOT"/artifact/engine-rms ]]; then
    git -C "$ENGINE_REPO" worktree remove --force "$SNAP_ENGINE" >/dev/null 2>&1 || true
  fi
  if [[ "$SNAP_LARAVEL" == "$TEMP_ROOT"/artifact/papa-website-v2 ]]; then
    git -C "$LARAVEL_REPO" worktree remove --force "$SNAP_LARAVEL" >/dev/null 2>&1 || true
  fi
  if [[ -n "$TEMP_ROOT" && "$TEMP_ROOT" == /tmp/tmp.* ]]; then
    rm -rf -- "$TEMP_ROOT"
  fi
}
trap cleanup EXIT

for repo in "$ENGINE_REPO" "$LARAVEL_REPO"; do
  if [[ -n "$(git -C "$repo" status --porcelain)" ]]; then
    echo "Refusing dirty source repository: $repo" >&2
    exit 2
  fi
done

git -C "$ENGINE_REPO" worktree add --detach "$SNAP_ENGINE" "$ENGINE_REF" >"$TEMP_LOGS/engine-snapshot.log" 2>&1
git -C "$LARAVEL_REPO" worktree add --detach "$SNAP_LARAVEL" "$LARAVEL_REF" >"$TEMP_LOGS/laravel-snapshot.log" 2>&1
{
  printf 'engine_ref=%s\nengine_commit=%s\nengine_status=%s\n' "$ENGINE_REF" "$(git -C "$SNAP_ENGINE" rev-parse HEAD)" "$(git -C "$SNAP_ENGINE" status --porcelain)"
  printf 'laravel_ref=%s\nlaravel_commit=%s\nlaravel_status=%s\n' "$LARAVEL_REF" "$(git -C "$SNAP_LARAVEL" rev-parse HEAD)" "$(git -C "$SNAP_LARAVEL" status --porcelain)"
} >"$TEMP_LOGS/source-identity.log"
if [[ "$SNAP_CLEAN" == "$SNAP_PACKAGE/runs/clean-environment" ]]; then
  rm -rf -- "$SNAP_CLEAN"
fi
COMPOSE_FILE="$SNAP_PACKAGE/docker-compose.yml"

ARTIFACT_DOCKER_PATH="$(cygpath -m "$ARTIFACT_ROOT")"
cat >"$OVERRIDE_FILE" <<EOF
services:
  app-laravel:
    volumes:
      - "${ARTIFACT_DOCKER_PATH}:/artifact"
  rule-engine-go:
    volumes:
      - "${ARTIFACT_DOCKER_PATH}:/artifact"
  validation-runner:
    volumes:
      - "${ARTIFACT_DOCKER_PATH}:/artifact"
    environment:
      CLEAN_OUTPUTS: "1"
      SOURCE_SNAPSHOT_VERIFIED: "1"
EOF

BUILD_EXIT=0
START_EXIT=0
VALIDATION_EXIT=0
FAILURE_STAGE="VALIDATION_RUNNER"
FAILURE_REASON=""
PRIMARY_LOG="raw-logs/validation-runner.log"

set +e
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" -f "$OVERRIDE_FILE" build --no-cache >"$TEMP_LOGS/docker-build.log" 2>&1
BUILD_EXIT=$?
set -e

if [[ "$BUILD_EXIT" -ne 0 ]]; then
  VALIDATION_EXIT="$BUILD_EXIT"
  FAILURE_STAGE="DOCKER_BUILD"
  FAILURE_REASON="docker compose build --no-cache failed"
  PRIMARY_LOG="raw-logs/docker-build.log"
else
  set +e
  docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" -f "$OVERRIDE_FILE" up -d --wait mysql app-laravel rule-engine-go >"$TEMP_LOGS/service-start.log" 2>&1
  START_EXIT=$?
  set -e
  if [[ "$START_EXIT" -ne 0 ]]; then
    VALIDATION_EXIT="$START_EXIT"
    FAILURE_STAGE="SERVICE_READINESS"
    FAILURE_REASON="one or more clean services failed readiness"
    PRIMARY_LOG="raw-logs/service-start.log"
  else
    set +e
    docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" -f "$OVERRIDE_FILE" run --name "$CONTAINER_NAME" validation-runner >"$TEMP_LOGS/validation-runner.log" 2>&1
    VALIDATION_EXIT=$?
    set -e
  fi
fi

if [[ "$BUILD_EXIT" -eq 0 ]]; then
  docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" -f "$OVERRIDE_FILE" logs --no-color mysql >"$TEMP_LOGS/mysql.log" 2>&1 || true
  docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" -f "$OVERRIDE_FILE" logs --no-color app-laravel >"$TEMP_LOGS/app-laravel.log" 2>&1 || true
  docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" -f "$OVERRIDE_FILE" logs --no-color rule-engine-go >"$TEMP_LOGS/rule-engine-go.log" 2>&1 || true
  docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" -f "$OVERRIDE_FILE" images -q | sort -u | while read -r image_id; do
    [[ -n "$image_id" ]] && docker image inspect "$image_id" --format '{{json .}}'
  done >"$TEMP_LOGS/docker-images.json"
else
  : >"$TEMP_LOGS/docker-images.json"
fi

CONTAINER_ID="$(docker inspect --format '{{.Id}}' "$CONTAINER_NAME" 2>/dev/null || true)"
RUNNER_ID="$(docker info --format '{{.ID}}' 2>/dev/null || true)"
RUNNER_OS="$(docker info --format '{{.OperatingSystem}} {{.KernelVersion}}' 2>/dev/null || true)"
RUNNER_ARCH="$(docker info --format '{{.Architecture}}' 2>/dev/null || true)"
mkdir -p "$SNAP_CLEAN/raw-logs"
cp "$TEMP_LOGS"/* "$SNAP_CLEAN/raw-logs/" 2>/dev/null || true

FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DURATION="$(( $(date +%s) - START_SECONDS ))"
set +e
python "$SNAP_PACKAGE/finalize_clean_run.py" \
  --exit-code "$VALIDATION_EXIT" --started-at "$STARTED_AT" --finished-at "$FINISHED_AT" \
  --duration-seconds "$DURATION" --container-id "$CONTAINER_ID" --run-id "$RUN_ID" \
  --failure-stage "$FAILURE_STAGE" --failure-reason "$FAILURE_REASON" --primary-log "$PRIMARY_LOG" \
  --runner-id "$RUNNER_ID" --runner-os "$RUNNER_OS" --runner-architecture "$RUNNER_ARCH"
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
