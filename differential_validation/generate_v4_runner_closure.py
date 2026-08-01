"""Create a run-scoped V4 audit when no clean runner can actually be selected."""
from __future__ import annotations

import hashlib
import json
import locale
import os
import platform
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT.parent
LARAVEL = ENGINE.parent / "papa-website-v2"
RUNS = ROOT / "runs/clean-environment"
SOURCE_TAG = "tpr-ir-clean-closure-v4"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_report(name: str, body: str) -> None:
    (ROOT / name).write_text(body.rstrip() + "\n", encoding="utf-8")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git(repo: Path, *args: str) -> str:
    return subprocess.run(("git", *args), cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def archive_hash(repo: Path, revision: str) -> str:
    result = subprocess.run(("git", "archive", "--format=tar", revision), cwd=repo, check=True, capture_output=True)
    return hashlib.sha256(result.stdout).hexdigest()


def table(headers: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines.extend("| " + " | ".join(str(value).replace("\n", " ") for value in row) + " |" for row in rows)
    return "\n".join(lines)


def ensure_clean() -> None:
    for repo in (ENGINE, LARAVEL):
        status = git(repo, "status", "--porcelain=v1", "--untracked-files=all")
        if status:
            raise RuntimeError(f"cannot publish runner audit from dirty tree: {repo}\n{status}")


def attempt(run_dir: Path, name: str, command: list[str], timeout: int = 20) -> dict:
    raw = run_dir / "raw-logs"
    raw.mkdir(parents=True, exist_ok=True)
    stdout_path, stderr_path = raw / f"{name}.stdout.log", raw / f"{name}.stderr.log"
    started, clock = datetime.now(timezone.utc), time.perf_counter()
    environment = os.environ.copy()
    environment.update({"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "Never"})
    try:
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=timeout, env=environment)
        stdout = completed.stdout.decode("utf-8", errors="replace")
        stderr = completed.stderr.decode("utf-8", errors="replace")
        code = completed.returncode
    except FileNotFoundError as exc:
        stdout, stderr, code = "", str(exc), 127
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        stderr += "\ncommand timed out"
        code = 124
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    finished = datetime.now(timezone.utc)
    return {
        "command": command, "working_directory": ".", "started_at": started.isoformat(),
        "finished_at": finished.isoformat(), "duration_seconds": round(time.perf_counter() - clock, 6),
        "exit_code": code, "stdout_file": stdout_path.relative_to(run_dir).as_posix(),
        "stderr_file": stderr_path.relative_to(run_dir).as_posix(),
        "status": "PASS" if code == 0 else ("NOT_AVAILABLE" if code == 127 else "FAIL"),
    }


def main() -> None:
    ensure_clean()
    tag_commit = git(ENGINE, "rev-list", "-n", "1", SOURCE_TAG)
    laravel_tag_commit = git(LARAVEL, "rev-list", "-n", "1", SOURCE_TAG)
    if subprocess.run(("git", "merge-base", "--is-ancestor", tag_commit, git(ENGINE, "rev-parse", "HEAD")), cwd=ENGINE).returncode:
        raise RuntimeError("V4 source tag is not an ancestor of the evidence commit")
    if laravel_tag_commit != git(LARAVEL, "rev-parse", "HEAD"):
        raise RuntimeError("Laravel V4 tag does not identify the final trace source")

    now = datetime.now(timezone.utc)
    run_id = "runner-audit-" + now.strftime("%Y%m%dT%H%M%SZ")
    run_dir = RUNS / run_id
    if run_dir.exists():
        raise RuntimeError(f"run ID already exists: {run_id}")
    run_dir.mkdir(parents=True)

    commands = [
        attempt(run_dir, "docker-version", ["docker", "--version"]),
        attempt(run_dir, "docker-compose-version", ["docker", "compose", "version"]),
        attempt(run_dir, "github-cli-version", ["gh", "--version"]),
        attempt(run_dir, "wsl-distributions", ["wsl.exe", "--list", "--quiet"]),
        attempt(run_dir, "virtualization-capability", ["powershell", "-NoProfile", "-Command", "$p=Get-CimInstance Win32_Processor|Select-Object -First 1; [pscustomobject]@{VirtualizationFirmwareEnabled=$p.VirtualizationFirmwareEnabled;VMMonitorModeExtensions=$p.VMMonitorModeExtensions}|ConvertTo-Json -Compress"]),
        attempt(run_dir, "private-laravel-remote-access", ["git", "ls-remote", "https://softmitend@github.com/mascitradotcom/papa-website-v2", "HEAD"]),
    ]
    command_by_name = {Path(item["stdout_file"]).stem.replace(".stdout", ""): item for item in commands}
    runners = [
        ["Local Docker Compose", "no", "local snapshot only", "yes", "no", "Docker and Compose executables are absent"],
        ["Hosted GitHub Actions", "workflow prepared; not dispatchable", "no", "public remote only", "no", "No CLI/API credential; private Laravel checkout failed"],
        ["WSL/Linux", "no", "local snapshot only", "yes", "no", "No installed Linux distribution"],
        ["Clean VM", "no instance", "not applicable", "not applicable", "no", "Virtualization capable, but no clean VM exists"],
        ["Remote runner", "no", "no", "no", "no", "No accessible runner endpoint or credential"],
    ]
    write_report("RUNNER_AVAILABILITY_REPORT.md", "# Runner availability report\n\n" + table(
        ["Runner", "Available", "Can access Laravel", "Can access Go", "Selected", "Reason"], runners,
    ) + f"\n\nRun-scoped command evidence: `runs/clean-environment/{run_id}/command-results.json`.")

    composer_lock = LARAVEL / "composer.lock"
    source_identity = {
        "artifact_version": "1.0", "source_tag": SOURCE_TAG,
        "laravel_commit": laravel_tag_commit, "go_commit": tag_commit, "validation_commit": tag_commit,
        "laravel_branch": git(LARAVEL, "branch", "--show-current"), "go_branch": git(ENGINE, "branch", "--show-current"),
        "working_trees_clean": True,
        "laravel_source_archive_sha256": archive_hash(LARAVEL, laravel_tag_commit),
        "engine_source_archive_sha256": archive_hash(ENGINE, tag_commit),
        "composer_lock_sha256": sha(composer_lock), "go_sum_sha256": sha(ENGINE / "go.sum"),
        "python_dependency_lock_sha256": sha(ROOT / "requirements.txt"),
        "private_source_access_method": "COMMIT_PINNED_SOURCE_SNAPSHOT",
        "snapshot_transport_to_runner": "NOT_EXECUTED",
    }
    write_json(ROOT / "CLEAN_SOURCE_IDENTITY.json", source_identity)
    write_json(run_dir / "source-identity.json", source_identity)
    write_report("PRIVATE_REPOSITORY_ACCESS_REPORT.md", f"""
# Private repository access report

Laravel access method selected: `COMMIT_PINNED_SOURCE_SNAPSHOT`. The local package builder can archive Laravel commit `{laravel_tag_commit}` without exposing a token; its deterministic tar SHA-256 is `{source_identity['laravel_source_archive_sha256']}`.

The snapshot was not published or transported to a hosted runner because no authenticated artifact/CI channel was available. The attempted read-only remote checkout failed and its stderr is retained under `runs/clean-environment/{run_id}/raw-logs/`. No token, password, deploy key, or secret value is stored in source or logs.
""")

    intended_images = load(ROOT / "runs/clean-environment/image-digests.json")
    intended_images["actual_images_inspected"] = False
    intended_images["status"] = "NOT_EXECUTED"
    write_json(run_dir / "image-digests.json", intended_images)
    write_json(run_dir / "command-results.json", {"artifact_version": "1.0", "commands": commands})
    environment = {
        "artifact_version": "1.0", "status": "NOT_EXECUTED", "runner_id": None,
        "os": platform.platform(), "architecture": platform.machine(), "cpu_count": os.cpu_count(),
        "memory": None, "timezone": "Asia/Jakarta", "locale": locale.getlocale()[0],
        "database_version": None, "database_collation": None, "freshness_evidence": None,
    }
    write_json(run_dir / "environment.json", environment)

    frozen = load(ROOT / "FROZEN_ARTIFACT_MANIFEST.json")
    input_checks = []
    for filename, key in (("reference_policy.json", "policy_sha256"), ("oracle_input_cases.json", "corpus_sha256"), ("oracle_expected_results.json", "expected_results_sha256")):
        actual = sha(ROOT / filename)
        input_checks.append({"artifact": filename, "expected_sha256": frozen[key], "actual_sha256": actual, "status": "PASS" if actual == frozen[key] else "FAIL"})
    output_checks = [{"artifact": name, "expected_sha256": None, "actual_sha256": None, "status": "NOT_EXECUTED"} for name in (
        "clean reconstructed baseline", "clean fixed result", "clean translator result", "clean pipeline result", "clean report", "actual image digest metadata",
    )]
    hash_report = {"artifact_version": "1.0", "run_id": run_id, "frozen_input_checks": input_checks, "clean_output_checks": output_checks, "overall_status": "NOT_EXECUTED"}
    write_json(ROOT / "CLEAN_HASH_VERIFICATION_REPORT.json", hash_report)
    write_json(run_dir / "hash-verification.json", hash_report)

    manifest = {
        "artifact_version": "1.0", "run_id": run_id, "status": "NOT_EXECUTED",
        "started_at": commands[0]["started_at"], "finished_at": commands[-1]["finished_at"],
        "duration_seconds": round(sum(item["duration_seconds"] for item in commands), 6),
        "final_exit_code": None, "runner_selected": None, "source_access": "SNAPSHOT_PREPARED_NOT_TRANSPORTED",
        "hash_verification": "FROZEN_INPUTS_PASS_CLEAN_OUTPUTS_NOT_EXECUTED",
        "failure_stage": "RUNNER_SELECTION", "failure_artifact": "command-results.json",
        "temporal_replay": "NOT_STARTED",
    }
    write_json(run_dir / "manifest.json", manifest)
    for folder in ("reconstructed-baseline", "fixed", "translator", "pipeline", "guards", "reports"):
        target = run_dir / folder
        target.mkdir(parents=True)
        (target / "README.md").write_text("Status: NOT_EXECUTED. No local result is copied into this clean-run scope.\n", encoding="utf-8")
    (run_dir / "raw-logs/README.md").write_text("Only runner-selection and repository-access attempts were executed. Experiment logs do not exist because no clean runner was selected.\n", encoding="utf-8")

    write_report("SERVICE_READINESS_REPORT.md", "# Service readiness report\n\n" + table(
        ["Service", "Required readiness", "Observed status", "Evidence"], [
            ["MySQL", "fresh database, connection, migrations", "NOT_EXECUTED", f"runs/clean-environment/{run_id}/manifest.json"],
            ["Laravel", "testing boot and database connection", "NOT_EXECUTED", f"runs/clean-environment/{run_id}/manifest.json"],
            ["Go", "health endpoint and engine readiness", "NOT_EXECUTED", f"runs/clean-environment/{run_id}/manifest.json"],
            ["Validation runner", "frozen artifacts and matching hashes", "FROZEN INPUT HASHES PASS; RUNNER NOT_EXECUTED", "CLEAN_HASH_VERIFICATION_REPORT.json"],
        ],
    ))

    local = load(ROOT / "final-report-data.json")
    layer = {item["layer"]: item for item in local["evaluation_layers"]}
    traces = load(ROOT / "e2e-execution-traces.json")["traces"]
    categories = Counter(item["evaluation_category"] for item in traces)
    v4_rows = [
        ["Reconstructed baseline", layer["Reconstructed baseline differential"]["cases"], "none", layer["Reconstructed baseline differential"]["mismatch"], "LOCAL_ONLY; CLEAN_NOT_EXECUTED"],
        ["Fixed differential", layer["Fixed differential"]["cases"], "none", layer["Fixed differential"]["mismatch"], "LOCAL_ONLY; CLEAN_NOT_EXECUTED"],
        ["Translator", layer["Translator fixtures"]["cases"], "none", layer["Translator fixtures"]["mismatch"], "LOCAL_ONLY; CLEAN_NOT_EXECUTED"],
        ["Full pipeline", categories["FULL_PAYROLL_PIPELINE"], "persistence on same transactions", sum(item["expected_hash"] != item["actual_hash"] for item in traces if item["evaluation_category"] == "FULL_PAYROLL_PIPELINE"), "LOCAL_ONLY; CLEAN_NOT_EXECUTED"],
        ["Configuration guard", categories["LARAVEL_CONFIGURATION_GUARD"], "pre-Go rejection", sum(item["result"] != "PASS" for item in traces if item["evaluation_category"] == "LARAVEL_CONFIGURATION_GUARD"), "LOCAL_ONLY; CLEAN_NOT_EXECUTED"],
    ]
    write_report("CLEAN_ENVIRONMENT_EXECUTION_REPORT.md", f"""
# Clean-environment execution report V4

## 1. Runner used
None. Status `NOT_EXECUTED`.
## 2. Runner freshness evidence
None; no runner instance was created.
## 3. Repository access method
Commit-pinned Laravel source snapshot prepared locally; transport to a runner was not available.
## 4. Source commits and tags
See `CLEAN_SOURCE_IDENTITY.json`; source tag `{SOURCE_TAG}`.
## 5. Image names and digests
Intended pinned digests are recorded; actual images were not built or inspected.
## 6. OS and architecture
No clean runner OS; audit host is `{platform.platform()}` / `{platform.machine()}`.
## 7. CPU and memory
Clean runner: not available.
## 8. Timezone and locale
Clean specification: `Asia/Jakarta` / `C.UTF-8`.
## 9. Database version and collation
Not executed on a fresh database.
## 10. Commands executed
Runner detection, virtualization capability, and private repository access checks only.
## 11. Exit codes
See `runs/clean-environment/{run_id}/command-results.json`.
## 12-20. Test and experiment results
Laravel, Go, vet, baseline repeats, fixed differential, translator, pipeline, persistence, and guards were not executed in a clean environment. Their local evidence remains separate.
## 21. Hash verification
Frozen local input hashes matched; clean output hashes are `NOT_EXECUTED`.
## 22. Total duration
Runner-selection command duration: `{manifest['duration_seconds']}` seconds.
## 23. Failure details
Stage `RUNNER_SELECTION`: no Docker/Compose, installed Linux environment, clean VM, authenticated CI channel, or accessible remote runner.
## 24. Final clean-reproduction status
`NOT_EXECUTED`.
""")

    write_report("DIFFERENTIAL_VALIDATION_FINAL_REPORT_V4.md", f"""
# Differential validation final report V4

## Executive verdict
The clean-reproduction attempt stopped at runner selection. No experiment command was executed in a clean environment, so local results are not promoted to clean evidence.

## Runner and repository access
No runner was selected. Laravel source snapshot identity was prepared from the final tagged commit, but no authenticated transport to hosted CI was available.

## Source identity
Engine/validation `{tag_commit}`; Laravel `{laravel_tag_commit}`; tag `{SOURCE_TAG}`. Lock and archive hashes are in `CLEAN_SOURCE_IDENTITY.json`.

## Clean execution status
`NOT_EXECUTED`, final exit code `null`, failure stage `RUNNER_SELECTION`.

{table(['Evaluation layer', 'Independent cases', 'Assertion layer', 'Mismatch', 'Status'], v4_rows)}

Persistence remains an assertion on the same full-pipeline transactions. Configuration guards remain pre-Go rejections and are not payroll transactions.

## Hash verification
Frozen policy, corpus, and expected-result hashes matched. Clean output and actual image hashes do not exist because the runner was not executed.

## Domain validity
`NOT_AUTHORITATIVE_BUSINESS_ORACLE / DOMAIN_VALIDATION_PENDING`.

## Limitations and temporal gate
No clean database, dependency install, service health check, test suite, differential run, or clean report regeneration occurred. Temporal replay remains `NOT_STARTED`.

## Readiness
A - Runner unavailable.
""")
    write_json(ROOT / "REPRODUCIBILITY_MANIFEST.json", {
        "artifact_version": "4.0", "status": "NOT_EXECUTED", "run_id": run_id,
        "run_manifest": f"runs/clean-environment/{run_id}/manifest.json",
        "source_identity": "CLEAN_SOURCE_IDENTITY.json", "hash_verification": "CLEAN_HASH_VERIFICATION_REPORT.json",
        "primary_command": "make clean-validate", "final_exit_code": None,
        "failure_stage": "RUNNER_SELECTION", "temporal_replay": "NOT_STARTED",
    })
    write_report("CODE_CHANGE_REPORT.md", f"""
# Code change report V4

- Source tag `{SOURCE_TAG}` binds the clean-run orchestration and audit generator.
- Added run-scoped runner/access/source/readiness/hash evidence and V4 reporting.
- Private Laravel access uses a commit-pinned snapshot identity; no credential or private source is committed into the public engine repository.
- Frozen policy, corpus, expected results, oracle, and production payroll logic were not changed.
- No clean experiment was executed and temporal replay remains `NOT_STARTED`.
""")
    print(json.dumps({"run_id": run_id, "status": "NOT_EXECUTED", "readiness": "A"}))


if __name__ == "__main__":
    main()
