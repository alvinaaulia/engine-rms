"""Finalize a Docker/CI clean run; never upgrades a failed run to PASS."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLEAN = ROOT / "runs/clean-environment"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--started-at", required=True)
    parser.add_argument("--finished-at", required=True)
    parser.add_argument("--duration-seconds", type=float, required=True)
    parser.add_argument("--container-id", default="")
    args = parser.parse_args()

    status = "FAIL" if args.exit_code else "PASS_PENDING_ARTIFACT_CHECK"
    reason = "validation-runner returned non-zero" if args.exit_code else None
    try:
        baseline = load(ROOT / "runs/reconstructed-baseline/manifest.json")
        fixed = load(ROOT / "runs/fixed/mismatch_details.json")
        traces = load(ROOT / "e2e-execution-traces.json")["traces"]
        categories = Counter(item["evaluation_category"] for item in traces)
        frozen = load(ROOT / "FROZEN_ARTIFACT_MANIFEST.json")
        gates = frozen["expected_gates"]
        if len(baseline["repeat_runs"]) != gates["baseline_repeat_count"] or any(item["mismatch_count"] != gates["baseline_mismatch_count"] for item in baseline["repeat_runs"]):
            raise RuntimeError("reconstructed baseline differs from frozen repeat/mismatch gate")
        if baseline["repeat_runs"][0]["mismatch_case_ids"] != baseline["repeat_runs"][1]["mismatch_case_ids"]:
            raise RuntimeError("reconstructed mismatch IDs are unstable")
        if baseline["repeat_runs"][0]["mismatch_case_ids"] != gates["baseline_mismatch_case_ids"]:
            raise RuntimeError("reconstructed mismatch IDs differ from frozen gate")
        for filename, key in (("reference_policy.json", "policy_sha256"), ("oracle_input_cases.json", "corpus_sha256"), ("oracle_expected_results.json", "expected_results_sha256")):
            if sha(ROOT / filename) != frozen[key]:
                raise RuntimeError(f"frozen hash mismatch: {filename}")
        if fixed["mismatch_count"] != gates["fixed_mismatch_count"]:
            raise RuntimeError("fixed differential contains mismatch")
        if categories["FULL_PAYROLL_PIPELINE"] != gates["full_pipeline_cases"] or categories["LARAVEL_CONFIGURATION_GUARD"] != gates["configuration_guard_cases"]:
            raise RuntimeError("E2E category counts differ from frozen design")
        if any(item["result"] != "PASS" or item["expected_hash"] != item["actual_hash"] for item in traces):
            raise RuntimeError("E2E trace failure or hash mismatch")
        if args.exit_code:
            raise RuntimeError(reason)
        status = "PASS"
    except Exception as exc:  # the failure is persisted before returning non-zero
        status, reason = "FAIL", str(exc)

    image_output = CLEAN / "raw-logs/docker-images.json"
    image_digests = {"actual_images_inspected": image_output.exists(), "docker_compose_images_raw": image_output.relative_to(CLEAN).as_posix() if image_output.exists() else None}
    write(CLEAN / "image-digests.json", image_digests)
    write(CLEAN / "environment.json", {
        "artifact_version": "1.0", "execution_status": status, "runner_id": platform.node(),
        "container_ids": [args.container_id] if args.container_id else [], "os": platform.platform(),
        "architecture": platform.machine(), "timezone": "Asia/Jakarta", "locale": "C.UTF-8",
    })
    for source, destination in (
        (ROOT / "runs/reconstructed-baseline", CLEAN / "reconstructed-baseline"),
        (ROOT / "runs/fixed", CLEAN / "fixed"),
    ):
        if source.exists():
            shutil.copytree(source, destination, dirs_exist_ok=True)
    for source, destination in (
        (ROOT / "translation_validation_fixtures.json", CLEAN / "translator/translation_validation_fixtures.json"),
        (ROOT / "e2e-execution-traces.json", CLEAN / "e2e/e2e-execution-traces.json"),
        (ROOT / "DIFFERENTIAL_VALIDATION_FINAL_REPORT_V3.md", CLEAN / "reports/DIFFERENTIAL_VALIDATION_FINAL_REPORT_V3.md"),
    ):
        if source.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    manifest = {
        "artifact_version": "1.0", "status": status, "final_exit_code": args.exit_code,
        "started_at": args.started_at, "finished_at": args.finished_at,
        "total_duration_seconds": args.duration_seconds, "clean_runner_id": platform.node(),
        "container_id": args.container_id or None, "hash_verification": "PASS" if status == "PASS" else "FAIL",
        "reconstructed_baseline": "PASS" if status == "PASS" else "FAIL",
        "fixed_differential": "PASS" if status == "PASS" else "FAIL",
        "translator": "PASS" if status == "PASS" else "FAIL",
        "full_pipeline": "PASS" if status == "PASS" else "FAIL",
        "configuration_guards": "PASS" if status == "PASS" else "FAIL",
        "schema_validation": "PASS" if status == "PASS" else "FAIL",
        "report_generation": "PASS" if status == "PASS" else "FAIL",
        "reason": reason, "temporal_replay": "NOT_STARTED",
    }
    write(CLEAN / "manifest.json", manifest)
    if status != "PASS":
        raise SystemExit(args.exit_code or 1)


if __name__ == "__main__":
    main()
