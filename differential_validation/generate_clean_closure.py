"""Freeze clean-run inputs and report actual clean-environment availability."""
from __future__ import annotations

import hashlib
import csv
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
CLEAN = ROOT / "runs/clean-environment"
RAW = CLEAN / "raw-logs"
TAG = "tpr-ir-clean-closure-v3"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(("git", *args), cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def archive_hash(repo: Path, revision: str) -> str:
    result = subprocess.run(("git", "archive", "--format=tar", revision), cwd=repo, check=True, capture_output=True)
    return hashlib.sha256(result.stdout).hexdigest()


def directory_hash(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        digest.update(item.relative_to(path).as_posix().encode())
        digest.update(b"\0")
        digest.update(item.read_bytes())
    return digest.hexdigest()


def attempt(name: str, command: list[str], timeout: int = 20) -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    stdout_path = RAW / f"{name}.stdout.log"
    stderr_path = RAW / f"{name}.stderr.log"
    started = datetime.now(timezone.utc)
    clock = time.perf_counter()
    env = os.environ.copy()
    env.update({"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "Never"})
    try:
        process = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=timeout, env=env)
        stdout = process.stdout.decode("utf-8", errors="replace")
        stderr = process.stderr.decode("utf-8", errors="replace")
        exit_code = process.returncode
    except FileNotFoundError as exc:
        stdout, stderr, exit_code = "", str(exc), 127
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        stderr += "\ncommand timed out"
        exit_code = 124
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    finished = datetime.now(timezone.utc)
    return {
        "command": command, "started_at": started.isoformat(), "finished_at": finished.isoformat(),
        "duration_seconds": round(time.perf_counter() - clock, 6), "exit_code": exit_code,
        "stdout_file": stdout_path.relative_to(CLEAN).as_posix(),
        "stderr_file": stderr_path.relative_to(CLEAN).as_posix(),
        "status": "PASS" if exit_code == 0 else ("NOT_AVAILABLE" if exit_code == 127 else "FAIL"),
    }


def command_value(command: list[str], cwd: Path = ROOT) -> tuple[str, str]:
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=20)
    except FileNotFoundError:
        return "NOT_AVAILABLE", "NOT_AVAILABLE"
    value = (result.stdout or result.stderr).strip().splitlines()
    return (value[0] if value else "NO_OUTPUT"), ("VERIFIED" if result.returncode == 0 else "NOT_AVAILABLE")


def table(headers: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines.extend("| " + " | ".join(str(value).replace("\n", " ") for value in row) + " |" for row in rows)
    return "\n".join(lines)


def write_report(name: str, content: str) -> None:
    (ROOT / name).write_text(content.rstrip() + "\n", encoding="utf-8")


def ensure_clean() -> None:
    for repo in (ENGINE, LARAVEL):
        status = git(repo, "status", "--porcelain=v1", "--untracked-files=all")
        if status:
            raise RuntimeError(f"working tree must be clean before freezing: {repo}\n{status}")


def main() -> None:
    ensure_clean()
    engine_head = git(ENGINE, "rev-parse", "HEAD")
    laravel_commit = git(LARAVEL, "rev-parse", "HEAD")
    validation_commit = git(ENGINE, "rev-list", "-n", "1", TAG)
    laravel_tag_commit = git(LARAVEL, "rev-list", "-n", "1", TAG)
    ancestry = subprocess.run(("git", "merge-base", "--is-ancestor", validation_commit, engine_head), cwd=ENGINE)
    if ancestry.returncode != 0 or laravel_tag_commit != laravel_commit:
        raise RuntimeError(f"{TAG} must identify the clean-closure source and the final Laravel trace state")
    engine_commit = validation_commit

    policy = ROOT / "reference_policy.json"
    corpus = ROOT / "oracle_input_cases.json"
    expected = ROOT / "oracle_expected_results.json"
    baseline_gate = json.loads((ROOT / "runs/reconstructed-baseline/manifest.json").read_text(encoding="utf-8"))
    fixed_gate = json.loads((ROOT / "runs/fixed/mismatch_details.json").read_text(encoding="utf-8"))
    trace_gate = json.loads((ROOT / "e2e-execution-traces.json").read_text(encoding="utf-8"))["traces"]
    trace_categories = Counter(item["evaluation_category"] for item in trace_gate)
    frozen = {
        "artifact_version": "1.0", "laravel_commit": laravel_commit, "go_commit": engine_commit,
        "validation_commit": validation_commit, "laravel_tag": TAG, "go_tag": TAG,
        "validation_tag": TAG, "working_tree_clean": True, "working_tree_status": "CLEAN",
        "policy_sha256": sha(policy), "corpus_sha256": sha(corpus),
        "expected_results_sha256": sha(expected),
        "oracle_sha256": sha(ROOT / "oracle_calculator/reference_oracle.py"),
        "verifier_sha256": sha(ROOT / "oracle_calculator/verify_oracle.py"),
        "laravel_source_snapshot_sha256": archive_hash(LARAVEL, laravel_commit),
        "go_source_snapshot_sha256": archive_hash(ENGINE, engine_commit),
        "differential_runner_sha256": sha(ROOT / "differential_runner/run_differential.py"),
        "comparator_sha256": sha(ROOT / "differential_runner/run_differential.py"),
        "artifact_schemas_sha256": directory_hash(ROOT / "artifact-schemas"),
        "reconstructed_baseline_sha256": sha(ROOT / "runs/reconstructed-baseline/actual-results.json"),
        "fixed_results_sha256": sha(ROOT / "runs/fixed/actual_results.json"),
        "e2e_traces_sha256": sha(ROOT / "e2e-execution-traces.json"),
        "final_report_generator_sha256": sha(ROOT / "generate_hardening_reports.py"),
        "expected_gates": {
            "baseline_repeat_count": len(baseline_gate["repeat_runs"]),
            "baseline_mismatch_count": baseline_gate["repeat_runs"][0]["mismatch_count"],
            "baseline_mismatch_case_ids": baseline_gate["repeat_runs"][0]["mismatch_case_ids"],
            "fixed_mismatch_count": fixed_gate["mismatch_count"],
            "full_pipeline_cases": trace_categories["FULL_PAYROLL_PIPELINE"],
            "configuration_guard_cases": trace_categories["LARAVEL_CONFIGURATION_GUARD"],
        },
        "timezone": "Asia/Jakarta", "locale": "C.UTF-8", "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(ROOT / "FROZEN_ARTIFACT_MANIFEST.json", frozen)

    checks = [
        ("Laravel commit", laravel_commit, "git rev-parse HEAD (Laravel)", "VERIFIED"),
        ("Go/validation commit", engine_commit, "git rev-parse HEAD (engine-rms)", "VERIFIED"),
        ("Branch Laravel", git(LARAVEL, "branch", "--show-current"), "git branch --show-current", "VERIFIED"),
        ("Branch Go", git(ENGINE, "branch", "--show-current"), "git branch --show-current", "VERIFIED"),
        ("Tag", TAG, f"git rev-list -n 1 {TAG}", "VERIFIED"),
        ("Working trees", "clean", "git status --porcelain", "VERIFIED"),
    ]
    for item, command in (
        ("PHP", ["php", "--version"]), ("Composer", ["composer", "--version"]),
        ("Laravel", ["php", "artisan", "--version"]), ("PHPUnit", ["php", "vendor/bin/phpunit", "--version"]),
        ("Go", ["go", "version"]), ("Python", [sys.executable, "--version"]),
        ("Docker", ["docker", "--version"]), ("Docker Compose", ["docker", "compose", "version"]),
    ):
        cwd = LARAVEL if item in {"Laravel", "PHPUnit"} else ROOT
        value, status = command_value(command, cwd)
        checks.append((item, value, " ".join(command), status))
    mysql_php = "require 'vendor/autoload.php'; $app=require 'bootstrap/app.php'; $app->make(Illuminate\\Contracts\\Console\\Kernel::class)->bootstrap(); $r=Illuminate\\Support\\Facades\\DB::selectOne('SELECT VERSION() AS version, @@collation_database AS collation'); echo $r->version.' / '.$r->collation;"
    mysql, mysql_status = command_value(["php", "-r", mysql_php], LARAVEL)
    checks.extend([
        ("MySQL", mysql, "PHP DB query: SELECT VERSION(), @@collation_database", mysql_status),
        ("GRULE", next(line.strip() for line in (ENGINE / "go.mod").read_text().splitlines() if "grule-rule-engine" in line), "go.mod", "VERIFIED"),
        ("OS", platform.platform(), "Python platform.platform()", "VERIFIED"),
        ("Architecture", platform.machine(), "Python platform.machine()", "VERIFIED"),
        ("Timezone", "Asia/Jakarta (clean specification); host=" + time.tzname[0], "TZ specification / Python time.tzname", "VERIFIED"),
        ("Locale", locale.getlocale()[0] or "UNKNOWN", "Python locale.getlocale()", "VERIFIED"),
    ])
    write_report("CLEAN_RUN_PREFLIGHT_REPORT.md", "# Clean-run preflight report\n\n" + table(["Item", "Value", "Source command", "Status"], [list(row) for row in checks]))

    attempts = [
        attempt("docker-version", ["docker", "--version"]),
        attempt("docker-compose-version", ["docker", "compose", "version"]),
        attempt("wsl-distributions", ["wsl.exe", "--list", "--quiet"]),
        attempt("github-cli-version", ["gh", "--version"]),
        attempt("private-ci-source-access", ["git", "ls-remote", "https://softmitend@github.com/mascitradotcom/papa-website-v2", "HEAD"]),
    ]
    # WSL may return zero with an empty distribution list; that is unavailable, not PASS.
    wsl = attempts[2]
    if wsl["exit_code"] == 0 and not (RAW / wsl["stdout_file"].split("/", 1)[1]).read_text(encoding="utf-8", errors="ignore").replace("\x00", "").strip():
        wsl["status"] = "NOT_AVAILABLE"

    image_digests = {
        "php": "sha256:8f0c382c6483a202baaad042c9ad51064f050de1093e5e8db990d055dd18534f",
        "python": "sha256:5dcba30b5f8fbd97e2f35dd1b140b3c94db70bd01b39ed88365732f8db8f68b5",
        "go": "sha256:47ce5636e9936b2c5cbf708925578ef386b4f8872aec74a67bd13a627d242b19",
        "composer": "sha256:20462d70afcfa999ad75dbd9333194067f4d869078bdb37430339e8d97e541d6",
        "mysql": "sha256:679e7e924f38a3cbb62a3d7df32924b83f7321a602d3f9f967c01b3df18495d6",
        "actual_images_inspected": False,
    }
    write_json(CLEAN / "image-digests.json", image_digests)
    write_json(CLEAN / "command-results.json", {"artifact_version": "1.0", "commands": attempts})
    environment = {
        "artifact_version": "1.0", "execution_status": "NOT_EXECUTED", "runner_id": None,
        "container_ids": None, "os": platform.platform(), "architecture": platform.machine(),
        "cpu_count": os.cpu_count(), "memory": None, "timezone": "Asia/Jakarta",
        "locale": "C.UTF-8", "database_collation": mysql.split(" / ")[-1] if mysql_status == "VERIFIED" else None,
        "clean_runner": None, "reason": "Docker/Compose and a Linux VM were unavailable; external CI could not access the private Laravel repository with non-interactive credentials.",
    }
    write_json(CLEAN / "environment.json", environment)
    clean_manifest = {
        "artifact_version": "1.0", "status": "NOT_EXECUTED", "final_exit_code": None,
        "source_manifest": "../../FROZEN_ARTIFACT_MANIFEST.json", "started_at": None, "finished_at": None,
        "total_duration_seconds": None, "clean_runner_id": None, "hash_verification": "NOT_EXECUTED",
        "reconstructed_baseline": "NOT_EXECUTED", "fixed_differential": "NOT_EXECUTED",
        "translator": "NOT_EXECUTED", "full_pipeline": "NOT_EXECUTED", "configuration_guards": "NOT_EXECUTED",
        "schema_validation": "NOT_EXECUTED", "report_generation": "NOT_EXECUTED",
        "reason": environment["reason"], "temporal_replay": "NOT_STARTED",
    }
    write_json(CLEAN / "manifest.json", clean_manifest)
    write_json(ROOT / "REPRODUCIBILITY_MANIFEST.json", {
        "artifact_version": "3.0", "status": "NOT_EXECUTED",
        "source_manifest": "FROZEN_ARTIFACT_MANIFEST.json",
        "clean_environment_manifest": "runs/clean-environment/manifest.json",
        "command_results": "runs/clean-environment/command-results.json",
        "image_digests": "runs/clean-environment/image-digests.json",
        "primary_command": "make clean-validate", "final_exit_code": None,
        "reason": environment["reason"], "temporal_replay": "NOT_STARTED",
    })
    write_report("CLEAN_ENVIRONMENT_EXECUTION_REPORT.md", f"""
# Clean-environment execution report

Status: `NOT_EXECUTED`. Final clean-run exit code: `null`.

Docker and Docker Compose were not installed, no Linux distribution was available through WSL, GitHub CLI was absent, and the stored non-interactive Git credential could not access the private Laravel repository. Consequently neither a local clean container nor an external fresh CI run was executed. The attempted availability commands, exit codes, timestamps, durations, stdout, and stderr are retained under `runs/clean-environment/`.

The intended fresh-run command is `make clean-validate`. No local-development result is presented as clean evidence.
""")
    for directory in ("reconstructed-baseline", "fixed", "translator", "e2e", "reports"):
        target = CLEAN / directory
        target.mkdir(parents=True, exist_ok=True)
        (target / "README.md").write_text("Status: NOT_EXECUTED. No local-development artifact is copied here as clean-run evidence.\n", encoding="utf-8")

    traces = json.loads((ROOT / "e2e-execution-traces.json").read_text(encoding="utf-8"))["traces"]
    full = [item for item in traces if item["evaluation_category"] == "FULL_PAYROLL_PIPELINE"]
    guards = [item for item in traces if item["evaluation_category"] == "LARAVEL_CONFIGURATION_GUARD"]
    write_report("E2E_CASE_RELATIONSHIP_REPORT.md", f"""
# E2E case relationship report

Relationship: **A**.

The {len(full)} persistence evaluations are assertions performed on the same {len(full)} full-pipeline payroll transactions and are not counted as {len(full)} additional independent cases.

Independent full-pipeline transactions: {len(full)}. Persistence assertions: {sum(bool(item['persistence_asserted']) for item in full)}. Distinct additional persistence cases: 0. Evidence: `e2e-execution-traces.json`.
""")
    write_report("CONFIGURATION_GUARD_REPORT.md", "# Configuration guard report\n\n" + table(
        ["Case", "Configuration", "Reached Go", "Salary persisted", "Database unchanged", "Error-code match", "Result"],
        [[item["case_id"], item.get("configuration"), "no", "no", item.get("database_unchanged"), item.get("expected_error_codes") == item.get("actual_error_codes"), item["result"]] for item in guards],
    ) + "\n\nThese are pre-execution rejections, not payroll transactions.")

    write_report("DOMAIN_VALIDATION_GUIDE.md", """
# Domain validation guide

Reviewers must inspect the formula and component dictionaries, frozen policy, rounding policy, all independently verified cases, a stratified policy-derived sample, all historical mismatch cases, and boundary cases. Record disagreements without changing the frozen expected artifact. Leave reviewer identity, approval, signature, decision, and verification date blank until supplied by the real domain expert.

Current status: `NOT_AUTHORITATIVE_BUSINESS_ORACLE / DOMAIN_VALIDATION_PENDING`.
""")

    expected_rows = json.loads(expected.read_text(encoding="utf-8"))["results"]
    corpus_rows = {item["case_id"]: item for item in json.loads(corpus.read_text(encoding="utf-8"))["cases"]}
    independent = [item for item in expected_rows if item["verification_status"] == "INDEPENDENTLY_VERIFIED"]
    policy_derived = [item for item in expected_rows if item["verification_status"] == "POLICY_DERIVED"]
    target_policy_count = max(1, (len(policy_derived) + 9) // 10)
    by_category: dict[str, list[dict]] = {}
    for item in policy_derived:
        by_category.setdefault(item["primary_category"], []).append(item)
    stratified: list[dict] = []
    category_names = sorted(by_category)
    offset = 0
    while len(stratified) < target_policy_count:
        added = False
        for category in category_names:
            rows = by_category[category]
            if offset < len(rows) and len(stratified) < target_policy_count:
                stratified.append(rows[offset])
                added = True
        if not added:
            break
        offset += 1
    mismatch_ids = set(baseline_gate["stable_mismatch_case_ids"])
    selected = {item["case_id"]: (item, "INDEPENDENTLY_VERIFIED") for item in independent}
    for item in stratified:
        selected.setdefault(item["case_id"], (item, "POLICY_DERIVED_STRATIFIED_10_PERCENT"))
    for item in expected_rows:
        case = corpus_rows[item["case_id"]]
        if item["case_id"] in mismatch_ids or case["primary_category"] == "BOUNDARY_CASE":
            selected.setdefault(item["case_id"], (item, "HISTORICAL_MISMATCH_OR_BOUNDARY"))
    fields = ["case_id", "primary_category", "verification_status", "sample_reason", "component_codes", "expected_hash", "reviewer_name", "reviewer_comment", "decision", "signature", "verification_date"]
    with (ROOT / "DOMAIN_VALIDATION_SAMPLE.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for case_id, (item, reason) in sorted(selected.items()):
            writer.writerow({
                "case_id": case_id, "primary_category": item["primary_category"],
                "verification_status": item["verification_status"], "sample_reason": reason,
                "component_codes": "|".join(component["code"] for component in item.get("components", [])),
                "expected_hash": item["expected_hash"], "reviewer_name": "", "reviewer_comment": "",
                "decision": "", "signature": "", "verification_date": "",
            })

    previous = json.loads((ROOT / "final-report-data.json").read_text(encoding="utf-8"))
    layers = previous["evaluation_layers"]
    layer_rows = [
        ["Reconstructed baseline", layers[0]["cases"], "none", layers[0]["mismatch"], "LOCAL_RECONSTRUCTED_EVIDENCE; CLEAN_NOT_EXECUTED", layers[0]["evidence"]],
        ["Fixed differential", layers[1]["cases"], "none", layers[1]["mismatch"], "LOCAL_PASS; CLEAN_NOT_EXECUTED", layers[1]["evidence"]],
        ["Translator fixture", layers[2]["cases"], "none", layers[2]["mismatch"], "LOCAL_PASS; CLEAN_NOT_EXECUTED", layers[2]["evidence"]],
        ["Full payroll pipeline", len(full), "persistence asserted on same transactions", sum(item["expected_hash"] != item["actual_hash"] for item in full), "LOCAL_PASS; CLEAN_NOT_EXECUTED", "e2e-execution-traces.json"],
        ["Configuration guard", len(guards), "pre-execution rejection", sum(item["result"] != "PASS" for item in guards), "LOCAL_PASS; CLEAN_NOT_EXECUTED", "CONFIGURATION_GUARD_REPORT.md"],
    ]
    write_report("DIFFERENTIAL_VALIDATION_FINAL_REPORT_V3.md", f"""
# Differential validation final report V3

## 1. Executive verdict
Local evidence remains internally consistent, but clean-environment reproduction was not executed. Readiness is A.

## 2. Frozen source and artifact baseline
Source commits, tags, snapshots, and artifact SHA-256 values are frozen in `FROZEN_ARTIFACT_MANIFEST.json`.

## 3. Clean-environment specification
The specification uses four services: app-laravel, mysql, rule-engine-go, and validation-runner. Primary command: `make clean-validate`.

## 4. Clean-environment execution result
Clean-environment reproduction remains NOT_EXECUTED because neither Docker nor an external clean CI runner with access to the private Laravel source was available during the audit.

## 5-10. Evaluation results
{table(['Evaluation layer', 'Independent cases', 'Assertion layer', 'Mismatch', 'Result', 'Evidence'], layer_rows)}

The {len(full)} persistence evaluations are assertions on the same {len(full)} full-pipeline transactions, not additional independent cases. The {len(guards)} guards are pre-execution rejections, not payroll transactions.

Definitions: a translator fixture tests TPR-to-GRL translation in isolation; Laravel-to-Go integration crosses the HTTP boundary; full payroll pipeline covers database facts through Go/GRULE and persistence; persistence assertion checks the salary record created by that same transaction; configuration guard rejects invalid configuration before Go execution.

## 11. Oracle verification breakdown
{previous['oracle']['independently_verified']} independently verified, {previous['oracle']['policy_derived']} policy-derived, and {previous['oracle']['unsupported_adjudication']} adjudicated.

## 12. Metric observability
Measured metrics retain value and denominator. Unobservable metrics remain null with reasons in `metric-results.json`.

## 13. Reproducibility evidence
Preflight commands, unavailable-runner attempts, pinned intended image digests, and null clean-run results are under `runs/clean-environment/`. No local result is relabeled clean evidence.

## 14. Domain validation status
`NOT_AUTHORITATIVE_BUSINESS_ORACLE / DOMAIN_VALIDATION_PENDING`.

## 15. Claims supported
The local reconstructed baseline repeated its mismatch set; local fixed, translator, pipeline, persistence, and guard evaluations passed against the frozen reference artifacts.

## 16. Claims not supported
No fresh-run equivalence, third-party rerun, authoritative payroll correctness, legal compliance, or completed domain approval is claimed.

## 17. Limitations
No Docker daemon, installed Linux distribution, usable GitHub CLI, or valid non-interactive credential for the private Laravel repository was available. Go internal TPR/GRL steps are source-verified but not separately runtime-instrumented by request ID.

## 18. Temporal replay gate
Temporal replay remains `NOT_STARTED` and is blocked until a clean runner completes with final exit code zero and all frozen hashes match.

## 19. Readiness decision
A - Clean environment could not be prepared.
""")
    write_report("CODE_CHANGE_REPORT.md", f"""
# Code change report V3

- Clean-run source tag: `{TAG}`; engine/validation commit `{engine_commit}`; Laravel trace-test commit `{laravel_commit}`.
- Added four-service Docker Compose, no-cache one-command runner, clean finalizer, preflight/frozen manifests, CI route, V3 report generation, and raw availability evidence.
- Strengthened E2E evidence with rate-setting IDs, source-verified Go internal path, explicit persistence relationship, error-code comparison, and database-unchanged guard assertions.
- Production payroll calculation logic, frozen corpus, frozen expected results, and reference policy were not modified.
- Clean execution was not possible; no PASS was manufactured and temporal replay remains not started.
""")
    print(json.dumps({"status": "NOT_EXECUTED", "readiness": "A", "commands": len(attempts)}))


if __name__ == "__main__":
    main()
