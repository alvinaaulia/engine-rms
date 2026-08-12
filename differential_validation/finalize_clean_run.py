"""Finalize an isolated clean run; never upgrades a failed run to PASS."""
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


def write_clean_reproduction_report(
    manifest: dict,
    baseline: dict,
    fixed_manifest: dict,
    fixed_mismatch: dict,
    traces: list[dict],
) -> None:
    """Write a run-scoped report from the evidence that was just finalized."""
    categories = Counter(item["evaluation_category"] for item in traces)
    exact_matches = sum(item.get("status") == "EXACT_MATCH" for item in traces)
    expected_rejections = sum(item.get("status") == "EXPECTED_REJECTION" for item in traces)
    persistence_assertions = sum(bool(item.get("persistence_asserted")) for item in traces)
    baseline_mismatches = [item["mismatch_count"] for item in baseline["repeat_runs"]]
    report = f"""# Clean-environment research evidence

## Verdict

The isolated `{manifest['runner_type']}` reproduction completed with status `{manifest['status']}` and exit code `{manifest['final_exit_code']}`. Source snapshot, environment preparation, service readiness, frozen-hash verification, reconstructed baseline, fixed differential validation, translator validation, full-pipeline validation, configuration guards, schema validation, and report generation all completed successfully.

## Frozen source pair

- Rule engine and evidence package: `{fixed_manifest['commits']['go']}`
- Laravel web application: `{fixed_manifest['commits']['laravel']}`
- Runner: `{manifest['clean_runner_id']}`
- Started: `{manifest['started_at']}`
- Finished: `{manifest['finished_at']}`
- Duration: `{manifest['total_duration_seconds']}` seconds

## Reproduced results

| Evaluation | Cases | Result |
|---|---:|---|
| Reconstructed baseline, repeat 1 | {fixed_manifest['results']['cases']} | {baseline_mismatches[0]} mismatches |
| Reconstructed baseline, repeat 2 | {fixed_manifest['results']['cases']} | {baseline_mismatches[1]} mismatches |
| Fixed differential | {fixed_manifest['results']['cases']} | {fixed_mismatch['mismatch_count']} mismatches across {fixed_mismatch['mismatched_case_count']} cases |
| Full payroll pipeline | {categories['FULL_PAYROLL_PIPELINE']} | {exact_matches} exact matches; {persistence_assertions} persistence assertions |
| Configuration guards | {categories['LARAVEL_CONFIGURATION_GUARD']} | {expected_rejections} expected rejections |

The reconstructed mismatch case IDs were stable across both repetitions. The fixed run used the same frozen corpus, expected results, and policy hashes as the baseline reconstruction.

## Claim boundary

This run supports clean-environment reproducibility and technical equivalence against the frozen reference oracle. It does not establish that the frozen oracle is an authoritative payroll, legal, or regulatory oracle. Domain-expert validation remains a separate requirement. Temporal replay v2 was not executed as part of this run and remains `NOT_STARTED` in the manifest.

## Machine-readable evidence

- `manifest.json`: final run gate
- `command-results.json`: recorded command outcomes and log references
- `reconstructed-baseline/manifest.json`: repeated baseline provenance
- `fixed/manifest.json`: fixed source, environment, and frozen hashes
- `fixed/mismatch_details.json`: zero-mismatch result
- `fixed/full_pipeline_e2e.json`: full-pipeline and persistence traces
- `raw-logs/`: command, service, tool-version, test, and validation logs
"""
    path = CLEAN / "reports" / "CLEAN_REPRODUCTION_REPORT.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--started-at", required=True)
    parser.add_argument("--finished-at", required=True)
    parser.add_argument("--duration-seconds", type=float, required=True)
    parser.add_argument("--container-id", default="")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--failure-stage", default="VALIDATION_RUNNER")
    parser.add_argument("--failure-reason", default="")
    parser.add_argument("--primary-log", default="raw-logs/validation-runner.log")
    parser.add_argument("--runner-id", default="")
    parser.add_argument("--runner-os", default="")
    parser.add_argument("--runner-architecture", default="")
    parser.add_argument("--runner-type", choices=("DOCKER", "WSL_NATIVE", "CI"), default="DOCKER")
    args = parser.parse_args()

    status = "FAIL" if args.exit_code else "PASS_PENDING_ARTIFACT_CHECK"
    reason = "validation-runner returned non-zero" if args.exit_code else None
    recorded_experiment_commands = False
    try:
        if args.exit_code and args.failure_stage != "VALIDATION_RUNNER":
            raise RuntimeError(args.failure_reason or f"{args.failure_stage} returned non-zero")
        baseline = load(ROOT / "runs/reconstructed-baseline/manifest.json")
        fixed = load(ROOT / "runs/fixed/mismatch_details.json")
        fixed_manifest = load(ROOT / "runs/fixed/manifest.json")
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
    if args.runner_type == "DOCKER":
        image_digests = {
            "applicable": True,
            "actual_images_inspected": image_output.exists(),
            "docker_compose_images_raw": image_output.relative_to(CLEAN).as_posix() if image_output.exists() else None,
        }
    else:
        image_digests = {
            "applicable": False,
            "actual_images_inspected": False,
            "docker_compose_images_raw": None,
            "reason": f"{args.runner_type} executes pinned host packages and lockfiles without container images",
        }
    write(CLEAN / "image-digests.json", image_digests)
    write(CLEAN / "environment.json", {
        "artifact_version": "1.0", "execution_status": status,
        "runner_type": args.runner_type,
        "runner_id": args.runner_id or platform.node(),
        "container_ids": [args.container_id] if args.container_id else [],
        "os": args.runner_os or platform.platform(),
        "architecture": args.runner_architecture or platform.machine(),
        "timezone": "Asia/Jakarta", "locale": "C.UTF-8",
    })
    command_results = []
    failed_command_summaries = []
    meta_roots = [
        ROOT / "runs/hardening/raw-logs", ROOT / "runs/fixed/raw-logs",
        ROOT / "runs/reconstructed-baseline/repeat-1/raw-logs",
        ROOT / "runs/reconstructed-baseline/repeat-2/raw-logs",
    ]
    for meta_root in meta_roots:
        if not meta_root.exists():
            continue
        prefix = "--".join(meta_root.relative_to(ROOT / "runs").parts[:-1])
        for meta_path in sorted(meta_root.glob("*.meta.json")):
            recorded_experiment_commands = True
            meta = load(meta_path)
            copied = {}
            for key in ("stdout_file", "stderr_file", "evidence_file"):
                source_name = meta.get(key)
                if not source_name:
                    continue
                source = meta_root / source_name
                if source.exists():
                    destination = CLEAN / "raw-logs" / f"{prefix}--{source.name}"
                    shutil.copy2(source, destination)
                    copied[key] = destination.relative_to(CLEAN).as_posix()
            evidence_exists = bool(copied.get("evidence_file"))
            command_status = "PASS" if meta["exit_code"] == 0 and evidence_exists else "FAIL"
            if command_status == "FAIL":
                failed_command_summaries.append(
                    f"{' '.join(meta['command'])} (exit_code={meta['exit_code']}, evidence_exists={evidence_exists})"
                )
            command_results.append({
                "command": meta["command"], "started_at": meta["started_at"], "finished_at": meta["finished_at"],
                "duration_seconds": meta["duration_seconds"], "exit_code": meta["exit_code"],
                "stdout_file": copied.get("stdout_file"), "stderr_file": copied.get("stderr_file"),
                "evidence_file": copied.get("evidence_file"),
                "status": command_status,
            })
    if args.exit_code and failed_command_summaries:
        reason = f"recorded command failed: {failed_command_summaries[0]}"
    wrapper_target = "clean-validate-wsl" if args.runner_type == "WSL_NATIVE" else "clean-validate"
    command_results.append({
        "command": ["make", wrapper_target], "started_at": args.started_at, "finished_at": args.finished_at,
        "duration_seconds": args.duration_seconds, "exit_code": args.exit_code,
        "working_directory": "differential_validation", "stdout_file": args.primary_log, "stderr_file": None,
        "evidence_file": "manifest.json", "status": status,
    })
    write(CLEAN / "command-results.json", {"artifact_version": "1.0", "commands": command_results})
    early_failure = args.failure_stage in {"SOURCE_SNAPSHOT", "ENVIRONMENT_PREPARATION", "DOCKER_BUILD", "SERVICE_READINESS"} or not recorded_experiment_commands
    if status == "FAIL" and args.failure_stage == "VALIDATION_RUNNER" and not recorded_experiment_commands:
        reason = args.failure_reason or "validation-runner exited before any recorded experiment command"
    for source, destination in (
        (ROOT / "runs/reconstructed-baseline", CLEAN / "reconstructed-baseline"),
        (ROOT / "runs/fixed", CLEAN / "fixed"),
    ):
        if source.exists() and not early_failure:
            shutil.copytree(source, destination, dirs_exist_ok=True)
    for source, destination in (
        (ROOT / "translation_validation_fixtures.json", CLEAN / "translator/translation_validation_fixtures.json"),
        (ROOT / "e2e-execution-traces.json", CLEAN / "e2e/e2e-execution-traces.json"),
    ):
        if source.exists() and not early_failure:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    experiment_status = "PASS" if status == "PASS" else ("NOT_EXECUTED" if early_failure else "FAIL")
    build_status = (
        "NOT_APPLICABLE" if args.runner_type != "DOCKER"
        else "FAIL" if args.failure_stage == "DOCKER_BUILD"
        else "PASS"
    )
    preparation_status = (
        "FAIL" if args.failure_stage in {"SOURCE_SNAPSHOT", "ENVIRONMENT_PREPARATION"}
        else "PASS"
    )
    readiness_status = (
        "NOT_EXECUTED" if args.failure_stage in {"SOURCE_SNAPSHOT", "ENVIRONMENT_PREPARATION", "DOCKER_BUILD"}
        else "FAIL" if args.failure_stage == "SERVICE_READINESS"
        else "PASS"
    )
    manifest = {
        "artifact_version": "1.0", "run_id": args.run_id, "status": status,
        "final_exit_code": args.exit_code, "failure_stage": None if status == "PASS" else args.failure_stage,
        "started_at": args.started_at, "finished_at": args.finished_at,
        "total_duration_seconds": args.duration_seconds,
        "clean_runner_id": args.runner_id or platform.node(),
        "runner_type": args.runner_type,
        "container_id": args.container_id or None,
        "environment_preparation": preparation_status,
        "docker_build": build_status, "service_readiness": readiness_status,
        "hash_verification": experiment_status,
        "reconstructed_baseline": experiment_status,
        "fixed_differential": experiment_status,
        "translator": experiment_status,
        "full_pipeline": experiment_status,
        "configuration_guards": experiment_status,
        "schema_validation": experiment_status,
        "report_generation": experiment_status,
        "reason": reason, "temporal_replay": "NOT_STARTED",
    }
    write(CLEAN / "manifest.json", manifest)
    if status == "PASS":
        write_clean_reproduction_report(manifest, baseline, fixed_manifest, fixed, traces)
    if status != "PASS":
        raise SystemExit(args.exit_code or 1)


if __name__ == "__main__":
    main()
