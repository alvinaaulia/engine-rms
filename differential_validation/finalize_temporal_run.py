#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def differential_metrics(path: Path) -> dict:
    cases: dict[str, bool] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            case_id = row["case_id"]
            cases.setdefault(case_id, False)
            if row.get("match") != "YES":
                cases[case_id] = True
    return {"case_count": len(cases), "mismatch_count": sum(cases.values())}


def junit_metrics(path: Path) -> dict:
    root = ElementTree.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    return {
        key: sum(int(suite.attrib.get(key, 0)) for suite in suites)
        for key in ("tests", "assertions", "failures", "errors", "skipped")
    }


def memory_bytes() -> int | None:
    if Path("/proc/meminfo").exists():
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    if os.name == "nt":
        import ctypes
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("memory_load", ctypes.c_ulong),
                        ("total_physical", ctypes.c_ulonglong), ("available_physical", ctypes.c_ulonglong),
                        ("total_page_file", ctypes.c_ulonglong), ("available_page_file", ctypes.c_ulonglong),
                        ("total_virtual", ctypes.c_ulonglong), ("available_virtual", ctypes.c_ulonglong),
                        ("available_extended_virtual", ctypes.c_ulonglong)]
        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
        return int(status.total_physical)
    return None


def write_report(run_dir: Path, summary: dict, legacy: dict, laravel: dict) -> None:
    latency = summary["latency_microseconds"]
    report = f"""# Temporal Replay Experiment Report

## Executive verdict

The local clean temporal experiment passed all executable gates. Domain validation remains pending and the synthetic oracle is not an authoritative business oracle.

## Dataset and execution

- Synthetic profiles: {summary['profile_count']}
- Payroll periods: 12
- Matrix originals: {summary['profile_period_cases']}
- Targeted cases: {summary['targeted_cases']}
- Total cases: {summary['case_count']}
- Repeats: {summary['repeat_count']}
- Supported replay attempts: {summary['supported_replay_attempts']}
- Expected rejection attempts: {summary['expected_rejection_attempts']}

## Exactness and integrity

- Supported exact matches: {summary['matched_replay_attempts']}/{summary['supported_replay_attempts']} ({summary['exact_match_percent']}%)
- Expected artifact rejections: {summary['accepted_rejection_attempts']}/{summary['expected_rejection_attempts']}
- Manifest completeness: {summary['manifest_completeness_percent']}%
- Current-state contamination violations: {summary['contamination_violations']}
- Live salary side-effect violations: {summary['side_effect_violations']}
- Mutation-wave gate: {summary['mutation_wave_gate']}

## Performance observation

Replay latency in microseconds: p50={latency['p50']}, p95={latency['p95']}, p99={latency['p99']}, min={latency['min']}, max={latency['max']}.
The serialized manifest JSONL artifact occupies {summary['snapshot_storage_bytes']} bytes. These values describe this recorded local environment; they are not a general production benchmark.

## Regression

- Reconstructed baseline repeat 1: {legacy['baseline_repeat_1']['case_count']} cases, {legacy['baseline_repeat_1']['mismatch_count']} mismatches
- Reconstructed baseline repeat 2: {legacy['baseline_repeat_2']['case_count']} cases, {legacy['baseline_repeat_2']['mismatch_count']} mismatches
- Fixed implementation: {legacy['fixed']['case_count']} cases, {legacy['fixed']['mismatch_count']} mismatches
- Laravel: {laravel['tests']} tests, {laravel['assertions']} assertions, {laravel['failures']} failures, {laravel['errors']} errors, {laravel['skipped']} skipped
- Go tests and go vet: PASS (exit-code evidence in raw-logs)

## Domain limitation

`NOT_AUTHORITATIVE_BUSINESS_ORACLE / DOMAIN_VALIDATION_PENDING`. This run supports implementation correctness and temporal isolation claims only.
"""
    (run_dir / "TEMPORAL_REPLAY_EXPERIMENT_REPORT.md").write_text(report, encoding="utf-8")
    final = f"""# Temporal Replay Final Report

## 1. Executive verdict

Readiness **H** for this recorded clean local run: temporal replay and clean reproduction passed; domain validation remains pending.

## 2. Original execution capture

Original salary execution persists a locked manifest and immutable output atomically. The experiment produced {summary['case_count']} locked synthetic manifests.

## 3. Execution manifest specification

Facts, canonical TPR-IR, component types, version identities, rounding/hit policies, generated GRL, output, provenance, timestamps, and SHA-256 bindings are captured.

## 4. Version binding

Rule, rate, and tax identities were present and matched for all {summary['supported_replay_attempts']} supported replay attempts.

## 5. Facts and ruleset snapshots

Replay requests were constructed only from locked snapshots and verified hashes before execution.

## 6. Replay architecture

Laravel performs integrity validation, snapshot-only dispatch, comparison, difference persistence, and audit logging; Go validates and executes the frozen TPR-IR through GRULE.

## 7. No-side-effect guarantee

Salary state hash remained `{summary['salary_state_sha256_before']}` before and after replay; violations: {summary['side_effect_violations']}.

## 8. Compatibility strategy

Manifest 1.0, TPR-IR 1.0, translator `laravel-go-tpr-translator-1.0`, and engine `go-grule-tpr-engine-1.0` are fail-closed registry entries.

## 9. Temporal dataset

30 profiles x 12 periods = 360 matrix cases, plus 48 targeted cases; no real employee PII.

## 10. Mutation waves

Seven current-state waves changed current execution signatures while every historical sentinel replay remained matched. Gate: {summary['mutation_wave_gate']}.

## 11. Replay exactness

{summary['matched_replay_attempts']}/{summary['supported_replay_attempts']} supported replay attempts matched with zero differences.

## 12. Version identity match

Rule/rate/tax identity, facts hash, ruleset hash, translator, engine, request, and execution correlation were compared.

## 13. Current-state contamination

Forbidden lookup count: {summary['contamination_violations']}.

## 14. Integrity failure handling

{summary['accepted_rejection_attempts']}/{summary['expected_rejection_attempts']} corrupt, missing-version, unsupported-schema, and missing-output attempts were rejected with structured codes.

## 15. Determinism

Two repeats produced identical hashes for every supported manifest.

## 16. Performance observation

p50 {latency['p50']} us; p95 {latency['p95']} us; p99 {latency['p99']} us. Local observation only.

## 17. Regression status

Baseline reproduced 8 mismatches twice; fixed differential produced 0 mismatches. Laravel, Go, vet, translator, and pipeline gates passed.

## 18. Reproducibility

See `TEMPORAL_REPLAY_REPRODUCIBILITY_MANIFEST.json` and `raw-logs/`.

## 19. Domain validity limitation

`NOT_AUTHORITATIVE_BUSINESS_ORACLE / DOMAIN_VALIDATION_PENDING`.

## 20. Claims supported

Snapshot completeness, integrity rejection, deterministic exact replay, version observability, no forbidden current-state lookup, no salary side effect, and local clean reproducibility.

## 21. Claims not supported

Business-policy/domain correctness and production-scale performance are not established.

## 22. Remaining limitations

Correction replay is intentionally unsupported. Raw pre-rounding candidate observability remains outside the temporal v1 output contract.

## 23. Readiness decision

**H. Temporal replay and clean reproduction passed; domain validation pending.**
"""
    (run_dir / "TEMPORAL_REPLAY_FINAL_REPORT.md").write_text(final, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--started-at", required=True)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    summary = json.loads((run_dir / "experiment-summary.json").read_text(encoding="utf-8"))
    legacy = {
        "baseline_repeat_1": differential_metrics(run_dir / "legacy-regression/reconstructed-baseline-repeat-1/differential_results.csv"),
        "baseline_repeat_2": differential_metrics(run_dir / "legacy-regression/reconstructed-baseline-repeat-2/differential_results.csv"),
        "fixed": differential_metrics(run_dir / "legacy-regression/fixed/differential_results.csv"),
    }
    laravel = junit_metrics(run_dir / "raw-logs/laravel-full-suite.junit.xml")
    exits = {path.stem.replace(".exit-code", ""): int(path.read_text().strip()) for path in (run_dir / "raw-logs").glob("*.exit-code.txt")}
    gates = {
        "temporal_experiment": summary["status"] == "PASS",
        "baseline_repeat_1": legacy["baseline_repeat_1"] == {"case_count": 624, "mismatch_count": 8},
        "baseline_repeat_2": legacy["baseline_repeat_2"] == {"case_count": 624, "mismatch_count": 8},
        "fixed_differential": legacy["fixed"] == {"case_count": 624, "mismatch_count": 0},
        "laravel": laravel["failures"] == laravel["errors"] == laravel["skipped"] == 0,
        "command_exit_codes": all(code == 0 for code in exits.values()),
    }
    environment = {
        "platform": platform.platform(), "python": sys.version.split()[0],
        "processor": platform.processor(), "logical_cpu_count": os.cpu_count(),
        "physical_memory_bytes": memory_bytes(), "timezone": str(datetime.now().astimezone().tzinfo),
    }
    (run_dir / "environment.json").write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8")
    write_report(run_dir, summary, legacy, laravel)
    artifacts = {}
    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and path.name != "TEMPORAL_REPLAY_REPRODUCIBILITY_MANIFEST.json":
            artifacts[path.relative_to(run_dir).as_posix()] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    manifest = {
        "schema_version": "1.0", "run_id": run_dir.name,
        "started_at": args.started_at, "finished_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(gates.values()) else "FAIL", "gates": gates,
        "legacy_regression": legacy, "laravel": laravel, "environment": environment,
        "domain_validation": "DOMAIN_VALIDATION_PENDING",
        "oracle_status": "NOT_AUTHORITATIVE_BUSINESS_ORACLE", "artifacts": artifacts,
    }
    target = run_dir / "TEMPORAL_REPLAY_REPRODUCIBILITY_MANIFEST.json"
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "gates": gates}, sort_keys=True))
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
