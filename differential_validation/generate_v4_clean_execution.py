"""Validate a successful clean WSL run and publish the final V4 evidence set."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ENGINE = ROOT.parent
LARAVEL = ENGINE.parent / "papa-website-v2"
RUNS = ROOT / "runs" / "clean-environment"
SOURCE_TAG = "tpr-ir-clean-closure-v4"


def load(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError(f"required evidence is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"required evidence is missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def write_report(name: str, body: str) -> Path:
    path = ROOT / name
    path.write_bytes((body.strip() + "\n").encode("utf-8"))
    return path


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ("git", "-c", f"safe.directory={repo.as_posix()}", *args),
        cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def archive_hash(repo: Path, revision: str) -> str:
    result = subprocess.run(
        ("git", "-c", f"safe.directory={repo.as_posix()}",
         "archive", "--format=tar", revision),
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return hashlib.sha256(result.stdout).hexdigest()


def table(headers: list[str], rows: list[list[object]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    lines.extend(
        "| " + " | ".join(str(value).replace("\n", " ") for value in row) + " |"
        for row in rows
    )
    return "\n".join(lines)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def parse_source_log(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            if key in {
                "engine_ref", "engine_commit", "engine_status",
                "laravel_ref", "laravel_commit", "laravel_status",
            }:
                values[key] = value
    required = {"engine_ref", "engine_commit", "laravel_ref", "laravel_commit"}
    require(required <= values.keys(), "source identity log is incomplete")
    return values


def parse_health_log(path: Path) -> tuple[dict[str, str], str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    db_line = next(
        (line for line in text.splitlines() if line.startswith("website_papa_v2_wsl_clean_testing\t")),
        "",
    )
    require(db_line, "database readiness row is absent")
    database, collation, server_timezone = db_line.split("\t")
    require("mysqld is alive" in text, "MySQL readiness did not pass")
    require("Environment ........................................................ testing" in text,
            "Laravel did not boot in the testing environment")
    return values, collation, server_timezone


def junit_summary(path: Path) -> dict[str, object]:
    root = ET.parse(path).getroot()
    suite = root if root.tag == "testsuite" else next(root.iter("testsuite"), None)
    require(suite is not None, f"JUnit suite is missing: {path}")
    def number(name: str, cast):
        return cast(suite.attrib.get(name, 0))
    return {
        "tests": number("tests", int),
        "assertions": number("assertions", int),
        "failures": number("failures", int),
        "errors": number("errors", int),
        "skipped": number("skipped", int),
        "time_seconds": number("time", float),
    }


def go_terminal_tests(path: Path, parent_name: str | None = None) -> tuple[int, int]:
    passed: set[str] = set()
    failed: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        name = item.get("Test")
        action = item.get("Action")
        if not name or action not in {"pass", "fail"}:
            continue
        if parent_name and not name.startswith(parent_name + "/"):
            continue
        (passed if action == "pass" else failed).add(name)
    return len(passed), len(failed)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="wsl-clean-20260802T090158Z")
    args = parser.parse_args()
    run = RUNS / args.run_id
    manifest = load(run / "manifest.json")
    commands_doc = load(run / "command-results.json")
    environment = load(run / "environment.json")
    images = load(run / "image-digests.json")
    baseline = load(run / "reconstructed-baseline" / "manifest.json")
    fixed_manifest = load(run / "fixed" / "manifest.json")
    fixed_mismatch = load(run / "fixed" / "mismatch-details.json")
    metrics_doc = load(run / "fixed" / "metrics.json")
    translator = load(run / "translator" / "translation_validation_fixtures.json")
    e2e = load(run / "e2e" / "e2e-execution-traces.json")
    frozen = load(ROOT / "FROZEN_ARTIFACT_MANIFEST.json")
    source = parse_source_log(run / "raw-logs" / "source-identity.log")
    health, db_collation, db_server_timezone = parse_health_log(
        run / "raw-logs" / "service-health.log"
    )

    require(manifest.get("status") == "PASS" and manifest.get("final_exit_code") == 0,
            "clean-run manifest is not PASS/0")
    require(manifest.get("runner_type") == "WSL_NATIVE", "unexpected runner type")
    expected_stages = {
        "environment_preparation", "service_readiness", "hash_verification",
        "reconstructed_baseline", "fixed_differential", "translator",
        "full_pipeline", "configuration_guards", "schema_validation", "report_generation",
    }
    require(all(manifest.get(key) == "PASS" for key in expected_stages),
            "one or more required clean-run stages did not pass")
    commands = commands_doc.get("commands", [])
    require(commands and all(item.get("exit_code") == 0 and item.get("status") == "PASS" for item in commands),
            "one or more recorded commands failed")
    require(any(item.get("command") == ["make", "clean-validate-wsl"] for item in commands),
            "WSL wrapper command evidence is missing")

    engine_commit = source["engine_commit"]
    laravel_commit = source["laravel_commit"]
    require(source["engine_ref"] == SOURCE_TAG and source["laravel_ref"] == SOURCE_TAG,
            "clean run did not use the final source tag")
    require(source.get("engine_status", "") == "" and source.get("laravel_status", "") == "",
            "clean source clones were dirty")
    require(git(ENGINE, "rev-list", "-n", "1", SOURCE_TAG) == engine_commit,
            "engine source tag no longer resolves to the executed commit")
    require(git(LARAVEL, "rev-list", "-n", "1", SOURCE_TAG) == laravel_commit,
            "Laravel source tag no longer resolves to the executed commit")

    frozen_files = {
        "reference_policy.json": "policy_sha256",
        "oracle_input_cases.json": "corpus_sha256",
        "oracle_expected_results.json": "expected_results_sha256",
    }
    frozen_checks = []
    for filename, key in frozen_files.items():
        expected = frozen[key]
        actual = sha256(ROOT / filename)
        require(actual == expected, f"frozen hash mismatch for {filename}")
        require(health.get(filename) == expected, f"clean readiness hash mismatch for {filename}")
        frozen_checks.append({
            "artifact": filename, "expected_sha256": expected,
            "actual_sha256": actual, "status": "PASS",
        })

    gates = frozen["expected_gates"]
    repeats = baseline.get("repeat_runs", [])
    require(len(repeats) == gates["baseline_repeat_count"], "baseline repeat count changed")
    require(all(item["mismatch_count"] == gates["baseline_mismatch_count"] for item in repeats),
            "baseline mismatch count changed")
    require(all(item["mismatch_case_ids"] == gates["baseline_mismatch_case_ids"] for item in repeats),
            "baseline mismatch IDs are not stable")
    require(len({item["semantic_results_hash"] for item in repeats}) == 1,
            "baseline semantic results are not repeatable")
    require(baseline.get("reproducibility_status") == "RECONSTRUCTED_REPRODUCED",
            "baseline reconstruction did not reproduce")
    require(fixed_mismatch.get("case_count") == 624, "fixed case count is not 624")
    require(fixed_mismatch.get("mismatch_count") == gates["fixed_mismatch_count"],
            "fixed differential has mismatches")
    require(fixed_manifest.get("results", {}).get("mismatches") == 0,
            "fixed manifest reports mismatches")

    metrics = {item["metric"]: item for item in metrics_doc.get("metrics", [])}
    metric_statuses = Counter(item.get("status") for item in metrics_doc.get("metrics", []))
    require(metric_statuses == {"MEASURED": 16, "NOT_OBSERVABLE": 4, "NOT_APPLICABLE": 2},
            "metric status counts are not 16 measured / 4 not observable / 2 not applicable")
    require(metrics.get("CASE_EXACT_MATCH", {}).get("value") == 624, "case exact match is incomplete")
    require(metrics.get("COMPONENT_EXACT_MATCH", {}).get("value") == 2592,
            "component exact match is incomplete")
    require(metrics.get("SUMMARY_EXACT_MATCH", {}).get("value") == 3600,
            "summary exact match is incomplete")
    require(metrics.get("RUNTIME_ERROR", {}).get("value") == 0, "runtime errors were observed")
    require(metrics.get("TIMEOUT", {}).get("value") == 0, "timeouts were observed")

    fixture_count = translator.get("fixture_count")
    require(fixture_count == len(translator.get("fixtures", [])) == 12,
            "translator fixture count is not 12")
    translator_pass, translator_fail = go_terminal_tests(
        run / "raw-logs" / "hardening--translator-hardening.stdout.log",
        "TestTranslationValidationFixtures",
    )
    require(translator_pass == fixture_count and translator_fail == 0,
            "translator subtest evidence is not 12/0")

    traces = e2e.get("traces", [])
    categories = Counter(item.get("evaluation_category") for item in traces)
    full_pipeline = [item for item in traces if item.get("evaluation_category") == "FULL_PAYROLL_PIPELINE"]
    guards = [item for item in traces if item.get("evaluation_category") == "LARAVEL_CONFIGURATION_GUARD"]
    require(e2e.get("case_count") == len(traces) == 36, "E2E trace count is not 36")
    require(len(full_pipeline) == gates["full_pipeline_cases"], "full-pipeline count is not 32")
    require(len(guards) == gates["configuration_guard_cases"], "configuration-guard count is not 4")
    require(all(item.get("result") == "PASS" and item.get("expected_hash") == item.get("actual_hash") for item in traces),
            "an E2E trace failed or mismatched")
    require(all(item.get("persistence_asserted") is True for item in full_pipeline),
            "persistence was not asserted on all 32 transactions")
    require(all(item.get("persistence_asserted") is not True for item in guards),
            "a configuration guard was incorrectly counted as a persisted transaction")

    laravel_junit = junit_summary(run / "raw-logs" / "hardening--laravel-tests-hardening.xml")
    e2e_junit = junit_summary(run / "fixed" / "raw-logs" / "e2e-hardening-junit.xml")
    require(laravel_junit == {
        "tests": 157, "assertions": 1587, "failures": 0, "errors": 0,
        "skipped": 0, "time_seconds": 654.32862,
    }, "full Laravel JUnit summary changed")
    laravel_console = (run / "raw-logs" / "hardening--laravel-tests-hardening.stdout.log").read_text(
        encoding="utf-8", errors="replace"
    )
    require(re.search(r"Tests:\s+2 deprecated, 155 passed \(1587 assertions\)", laravel_console) is not None,
            "Laravel console classification is not 155 passed / 2 deprecated")
    require(e2e_junit["tests"] == 1 and e2e_junit["assertions"] == 750
            and e2e_junit["failures"] == e2e_junit["errors"] == 0,
            "dedicated E2E JUnit failed")
    go_pass, go_fail = go_terminal_tests(run / "raw-logs" / "hardening--go-tests-hardening.stdout.log")
    require(go_fail == 0 and go_pass > 0, "Go package tests failed")
    require(any(item.get("command") == ["go", "vet", "./..."] for item in commands),
            "Go vet command evidence is missing")

    generated_at = datetime.now(timezone.utc).isoformat()
    source_identity = {
        "artifact_version": "4.0",
        "run_id": args.run_id,
        "source_tag": SOURCE_TAG,
        "engine_commit": engine_commit,
        "validation_commit": engine_commit,
        "laravel_commit": laravel_commit,
        "clean_clone_status": "CLEAN",
        "source_access_method": "COMMIT_PINNED_LOCAL_CLONE",
        "engine_source_archive_sha256": archive_hash(ENGINE, engine_commit),
        "laravel_source_archive_sha256": archive_hash(LARAVEL, laravel_commit),
        "go_sum_sha256": sha256(ENGINE / "go.sum"),
        "composer_lock_sha256": sha256(LARAVEL / "composer.lock"),
        "python_requirements_sha256": sha256(ROOT / "requirements.txt"),
        "source_identity_evidence": f"runs/clean-environment/{args.run_id}/raw-logs/source-identity.log",
    }
    write_json(ROOT / "CLEAN_SOURCE_IDENTITY.json", source_identity)
    write_json(run / "source-identity.json", source_identity)

    report_names: list[str] = []
    def report(name: str, body: str) -> None:
        write_report(name, body)
        report_names.append(name)

    report("RUNNER_AVAILABILITY_REPORT.md", f"""
# Runner availability report V4

| Runner | Availability | Selected | Result | Evidence |
|---|---|---|---|---|
| WSL 2 native Ubuntu | Available | Yes | PASS | `runs/clean-environment/{args.run_id}/environment.json` |
| Docker Compose | Intentionally not used | No | NOT_APPLICABLE | `runs/clean-environment/{args.run_id}/image-digests.json` |
| Hosted/remote runner | Not required for this closure | No | NOT_SELECTED | local commit-pinned source was available |

The selected runner was WSL 2 with an isolated workload: new commit-pinned source clones, a new Python virtual environment, isolated dependency caches, and a freshly recreated dedicated test schema. The Ubuntu base distribution and Windows MySQL server already existed; this was not a newly provisioned VM.
""")
    report("PRIVATE_REPOSITORY_ACCESS_REPORT.md", f"""
# Private repository access report V4

The clean workload used a local clone of the already-authorized private Laravel repository, pinned to tag `{SOURCE_TAG}` and commit `{laravel_commit}`. It did not request, print, or persist a GitHub token, deploy key, password, or other repository secret. Source identity and archive hashes are recorded in `CLEAN_SOURCE_IDENTITY.json`.

This is a commit-pinned local-source transfer into WSL, not proof that an unauthenticated third party can clone the private repository.
""")
    report("SERVICE_READINESS_REPORT.md", f"""
# Service readiness report V4

| Service | Readiness result | Observed evidence |
|---|---|---|
| MySQL | PASS | server responded; dedicated database `website_papa_v2_wsl_clean_testing`; collation `{db_collation}` |
| Laravel | PASS | Laravel 10.50.2 booted with environment `testing`; PHP {health.get('php')} |
| Go rule engine | PASS | {health.get('go')} and HTTP `/health` readiness gate passed |
| Frozen inputs | PASS | policy, corpus, and expected-result hashes matched the frozen manifest |
| Validation runner | PASS | all {len(commands)} recorded commands exited 0 |

Raw readiness evidence: `runs/clean-environment/{args.run_id}/raw-logs/service-health.log`.
""")
    report("CLEAN_ENVIRONMENT_EXECUTION_REPORT.md", f"""
# Clean-environment execution report V4

## Outcome

Run `{args.run_id}` completed with status `PASS` and exit code `0` in {manifest['total_duration_seconds']:.0f} seconds. It used WSL 2 native Ubuntu without Docker.

## Environment and freshness

| Field | Recorded value |
|---|---|
| OS / architecture | {environment['os']} / {environment['architecture']} |
| Timezone / locale | {environment['timezone']} (`WIB`) / {environment['locale']} |
| PHP / Composer | {health.get('php')} / 2.9.5 |
| Go / Python | 1.25.6 / 3.14.4 |
| MySQL client | 8.4.10 |
| Database | fresh dedicated schema `website_papa_v2_wsl_clean_testing` |
| Database collation / server timezone | {db_collation} / {db_server_timezone} |
| CPU / memory / peak memory | NOT_RECORDED / NOT_RECORDED / NOT_MEASURED |
| Container images | NOT_APPLICABLE; no Docker images were used |

Freshness applies to the workload, source clones, dependency environments/caches, and test database schema. The WSL distribution and Windows MySQL server were pre-existing shared infrastructure. The database server version was not recorded during this run; only the MySQL client version was recorded.

## Executed validation

| Layer | Result |
|---|---|
| Reconstructed baseline | PASS: two repeats, 624 cases each, stable 8 mismatches |
| Fixed differential | PASS: 624 cases, 0 mismatches |
| Translator | PASS: 12 fixtures, 0 failures |
| Full payroll pipeline | PASS: 32 independent transactions, 0 mismatches; persistence asserted on the same 32 |
| Configuration guards | PASS: 4 expected pre-Go rejections; not payroll transactions |
| Full Laravel suite | PASS: 157 tests, 1587 assertions, 0 failures/errors/skips; console classified 155 passed and 2 deprecated |
| Go tests / vet | PASS / PASS; Go JSON contains {go_pass} terminal pass events including parent and subtest nodes |
| Schema validation / report generation | PASS / PASS |

All {len(commands)} recorded commands and their timestamps, durations, streams, and exit codes are in `runs/clean-environment/{args.run_id}/command-results.json`. Temporal replay remains `NOT_STARTED`.
""")
    report("DIFFERENTIAL_VALIDATION_FINAL_REPORT_V4.md", f"""
# Differential validation final report V4

## Executive verdict

The clean WSL-native reproduction is `PASS`. Decision: **J — clean reproduction passed while domain validation remains pending**. This decision does not promote the reference oracle into an authoritative payroll/business oracle.

## Source and runner

Engine/validation commit `{engine_commit}` and Laravel commit `{laravel_commit}` were selected through tag `{SOURCE_TAG}` in clean source clones. The workload ran under WSL 2 native Ubuntu; Docker was not used.

## Differential and integration results

| Evaluation layer | Independent cases | Assertion layer | Mismatch/failure | Status |
|---|---:|---|---:|---|
| Reconstructed baseline, repeat 1 | 624 | differential comparison | 8 | RECONSTRUCTED_REPRODUCED |
| Reconstructed baseline, repeat 2 | 624 | differential comparison | 8 | RECONSTRUCTED_REPRODUCED |
| Fixed differential | 624 | differential comparison | 0 | PASS |
| Translator | 12 | fixture subtests | 0 | PASS |
| Full payroll pipeline | 32 | persistence on the same 32 transactions | 0 | PASS |
| Configuration guards | 4 | expected rejection before Go | 0 | PASS |

The stable reconstructed-baseline mismatch IDs are `{', '.join(baseline['stable_mismatch_case_ids'])}`. The original historical raw baseline remains unavailable; these are two newly executed reconstruction runs and are not presented as the original run.

The E2E artifact contains 36 traces in total: 32 full payroll transactions plus 4 configuration guards. The guards are not counted as transactions. The dedicated PHPUnit wrapper contains one test method with 750 assertions; the trace artifact is the case-level evidence for the 32 + 4 split.

## Exactness and observability

Fixed execution achieved 624/624 case exact matches, 2592/2592 component exact matches, and 3600/3600 summary exact matches, with zero runtime errors and zero timeouts. Sixteen metrics are measured. Four are `NOT_OBSERVABLE`: raw amount, exact rounding point, resolved rate-version identity, and resolved tax-version identity. Translation and persistence metrics are `NOT_APPLICABLE` inside the differential layer because they are evaluated by their dedicated layers.

## Test-suite evidence

The full Laravel JUnit result is 157 tests, 1587 assertions, 0 failures, 0 errors, and 0 skipped; the console reports 155 passed and 2 deprecated. Translator evidence is 12 fixture subtests, not 13 independent tests (the additional Go event is the parent test). Go package tests and `go vet ./...` both exited 0.

## Hash and domain status

Frozen policy `{frozen['policy_sha256']}`, corpus `{frozen['corpus_sha256']}`, and expected-results `{frozen['expected_results_sha256']}` matched both the checked source and clean readiness log. Output hashes are recorded in `CLEAN_HASH_VERIFICATION_REPORT.json`.

Domain status remains `NOT_AUTHORITATIVE_BUSINESS_ORACLE / DOMAIN_VALIDATION_PENDING`. Temporal replay remains `NOT_STARTED`.

## Limitations

- The WSL base distribution and Windows MySQL server were pre-existing; isolation/freshness applies to the workload and dedicated test schema, not to a new VM.
- The database server version, CPU model, available memory, and peak memory were not recorded during the run.
- No Docker image digest exists because the user-selected path intentionally did not use Docker.
- Private-source access proves reproducibility from an already-authorized local repository snapshot, not anonymous remote clone access.
""")
    report("CODE_CHANGE_REPORT.md", f"""
# Code change report V4

- Added a native WSL clean-validation path, source cloning, dependency isolation, readiness gates, raw-log capture, and run finalization.
- Made frozen JSON bytes reproducible across Windows and Linux and added canonical-JSON regression coverage.
- Added the Go `/health` readiness endpoint and validation.
- Required PHP GD for the Laravel suite and improved failure reporting.
- Corrected the Laravel tax effective-date comparison to use the business calendar date; its targeted regression tests passed before the clean run and the full clean Laravel suite subsequently passed.
- Preserved four failed WSL attempts as failure evidence instead of rewriting them as successful runs.
- Frozen policy, corpus, and expected results were not changed to manufacture a pass. Domain validation remains pending and temporal replay was not started.

Executed source: engine/validation `{engine_commit}`; Laravel `{laravel_commit}`.
""")

    output_paths = {
        "reconstructed_baseline_manifest": run / "reconstructed-baseline" / "manifest.json",
        "reconstructed_baseline_repeat_1": run / "reconstructed-baseline" / "repeat-1" / "actual_results.json",
        "reconstructed_baseline_repeat_2": run / "reconstructed-baseline" / "repeat-2" / "actual_results.json",
        "fixed_manifest": run / "fixed" / "manifest.json",
        "fixed_actual_results": run / "fixed" / "actual-results.json",
        "fixed_mismatch_details": run / "fixed" / "mismatch-details.json",
        "fixed_metrics": run / "fixed" / "metrics.json",
        "translator_fixtures": run / "translator" / "translation_validation_fixtures.json",
        "e2e_traces": run / "e2e" / "e2e-execution-traces.json",
        "laravel_junit": run / "raw-logs" / "hardening--laravel-tests-hardening.xml",
        "go_test_json": run / "raw-logs" / "hardening--go-tests-hardening.stdout.log",
        "v4_report": ROOT / "DIFFERENTIAL_VALIDATION_FINAL_REPORT_V4.md",
    }
    hash_report = {
        "artifact_version": "4.0",
        "run_id": args.run_id,
        "status": "PASS",
        "frozen_input_checks": frozen_checks,
        "clean_output_checks": [
            {"artifact": name, "sha256": sha256(path), "status": "PASS"}
            for name, path in output_paths.items()
        ],
        "container_image_digest_status": "NOT_APPLICABLE",
        "overall_status": "PASS",
    }
    write_json(ROOT / "CLEAN_HASH_VERIFICATION_REPORT.json", hash_report)
    write_json(run / "hash-verification.json", hash_report)

    reports_dir = run / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    for name in report_names:
        shutil.copy2(ROOT / name, reports_dir / name)
    for name in ("CLEAN_SOURCE_IDENTITY.json", "CLEAN_HASH_VERIFICATION_REPORT.json"):
        shutil.copy2(ROOT / name, reports_dir / name)

    reproducibility = {
        "artifact_version": "4.0",
        "generated_at": generated_at,
        "run_id": args.run_id,
        "status": "PASS",
        "decision": "J",
        "runner_type": "WSL_NATIVE",
        "docker": "NOT_APPLICABLE",
        "primary_command": "make clean-validate-wsl",
        "final_exit_code": 0,
        "source_identity": "CLEAN_SOURCE_IDENTITY.json",
        "run_manifest": f"runs/clean-environment/{args.run_id}/manifest.json",
        "command_results": f"runs/clean-environment/{args.run_id}/command-results.json",
        "hash_verification": "CLEAN_HASH_VERIFICATION_REPORT.json",
        "domain_status": "NOT_AUTHORITATIVE_BUSINESS_ORACLE / DOMAIN_VALIDATION_PENDING",
        "temporal_replay": "NOT_STARTED",
        "report_sha256": {
            name: sha256(ROOT / name) for name in report_names
        },
        "evidence_sha256": {
            "manifest.json": sha256(run / "manifest.json"),
            "command-results.json": sha256(run / "command-results.json"),
            "environment.json": sha256(run / "environment.json"),
            "image-digests.json": sha256(run / "image-digests.json"),
            "source-identity.json": sha256(run / "source-identity.json"),
            "hash-verification.json": sha256(run / "hash-verification.json"),
        },
    }
    write_json(ROOT / "REPRODUCIBILITY_MANIFEST.json", reproducibility)
    shutil.copy2(ROOT / "REPRODUCIBILITY_MANIFEST.json", reports_dir / "REPRODUCIBILITY_MANIFEST.json")
    generation_evidence = {
        "artifact_version": "1.0",
        "generated_at": generated_at,
        "run_id": args.run_id,
        "status": "PASS",
        "validated_recorded_commands": len(commands),
        "generated_reports": report_names,
    }
    write_json(ROOT / "V4_REPORT_GENERATION_EVIDENCE.json", generation_evidence)
    write_json(reports_dir / "V4_REPORT_GENERATION_EVIDENCE.json", generation_evidence)
    print(json.dumps({
        "run_id": args.run_id,
        "status": "PASS",
        "decision": "J",
        "commands": len(commands),
        "reports": len(report_names),
    }))


if __name__ == "__main__":
    main()
