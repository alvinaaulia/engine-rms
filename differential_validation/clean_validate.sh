#!/usr/bin/env bash
set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_DIR="${ENGINE_DIR:-$(cd "$PACKAGE_DIR/.." && pwd)}"
LARAVEL_DIR="${LARAVEL_DIR:-$(cd "$ENGINE_DIR/../papa-website-v2" && pwd)}"

composer install --working-dir "$LARAVEL_DIR" --no-interaction --prefer-dist --no-progress
python -m pip install --no-cache-dir -r "$PACKAGE_DIR/requirements.txt"

export USE_EXTERNAL_FIXED_ENGINE=1
export RULE_ENGINE_URL="${RULE_ENGINE_URL:-http://rule-engine-go:8081}"
export ALLOW_DIRTY="${ALLOW_DIRTY:-0}"
exec bash "$PACKAGE_DIR/run_all.sh"
