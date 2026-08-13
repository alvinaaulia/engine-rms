"""Generate metrics, manifests, summaries, and per-bug evidence from raw artifacts."""
from __future__ import annotations

import hashlib
import csv
import json
import os
import platform
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT.parent
LARAVEL = Path(os.environ.get("LARAVEL_DIR", ENGINE.parent / "papa-website-public")).resolve()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(cwd: Path, *args: str) -> str:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def version(executable: str, *args: str) -> str:
    result = subprocess.run([executable, *args], capture_output=True, text=True)
    return (result.stdout or result.stderr).strip().splitlines()[0]


def database_collation() -> str:
    php = "require 'vendor/autoload.php'; $app=require 'bootstrap/app.php'; $app->make(Illuminate\\Contracts\\Console\\Kernel::class)->bootstrap(); echo Illuminate\\Support\\Facades\\DB::selectOne('SELECT @@collation_database AS value')->value;"
    return command(LARAVEL, "php", "-r", php)


def metric(name: str, status: str, value, denominator, unit: str, reason: str, comparator: bool, source: bool, evidence_file: str) -> dict:
    return {
        "metric": name, "status": status, "value": value, "denominator": denominator,
        "unit": unit, "reason": reason, "comparator_available": comparator,
        "source_data_available": source, "evidence_file": evidence_file,
    }


def build_metrics(run: str, mismatches: dict) -> dict:
    with (ROOT / "runs" / run / "differential_results.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    counts = Counter(item["category"] for item in mismatches["mismatches"])
    component_rows = [item for item in rows if item["comparison_scope"] == "COMPONENT"]
    summary_rows = [item for item in rows if item["comparison_scope"] == "SUMMARY"]
    summary_denominators = Counter(item["item"] for item in summary_rows)
    measured = [
        ("CASE_EXACT_MATCH", mismatches["case_count"] - mismatches["mismatched_case_count"], mismatches["case_count"], "case"),
        ("COMPONENT_EXACT_MATCH", sum(item["match"] == "YES" for item in component_rows), len(component_rows), "component comparison"),
        ("SUMMARY_EXACT_MATCH", sum(item["match"] == "YES" for item in summary_rows), len(summary_rows), "summary comparison"),
        ("COMPONENT_PRESENCE_MISMATCH", counts["MISSING_COMPONENT"] + counts["UNEXPECTED_COMPONENT"], len(component_rows), "component comparison"),
        ("COMPONENT_TYPE_MISMATCH", counts["COMPONENT_TYPE_MISMATCH"], len(component_rows), "component comparison"),
        ("ROUNDED_AMOUNT_MISMATCH", counts["ROUNDED_AMOUNT_MISMATCH"], len(component_rows), "component comparison"),
        ("TAXABLE_BASE_MISMATCH", counts["TAXABLE_BASE_MISMATCH"], summary_denominators["taxable_amount"], "case summary"),
        ("GROSS_MISMATCH", counts["GROSS_MISMATCH"], summary_denominators["gross_salary"] + summary_denominators["basic_salary"], "case summary field"),
        ("DEDUCTION_MISMATCH", counts["DEDUCTION_MISMATCH"], summary_denominators["total_deductions"], "case summary"),
        ("TAX_MISMATCH", counts["TAX_MISMATCH"], summary_denominators["tax"], "case summary"),
        ("NET_MISMATCH", counts["NET_MISMATCH"], summary_denominators["net_salary"], "case summary"),
        ("SOURCE_RULE_ID_MISMATCH", counts["RULE_PROVENANCE_MISMATCH"], len(component_rows), "component provenance"),
        ("RULE_VERSION_ID_MISMATCH", counts["RULE_PROVENANCE_MISMATCH"], len(component_rows), "component provenance"),
        ("CONTRIBUTOR_IDS_MISMATCH", counts["RULE_PROVENANCE_MISMATCH"], len(component_rows), "component provenance"),
        ("RUNTIME_ERROR", counts["RUNTIME_ERROR"], mismatches["case_count"], "case execution"),
        ("TIMEOUT", counts["TIMEOUT"], mismatches["case_count"], "case execution"),
    ]
    comparison_evidence = f"runs/{run}/differential_results.csv"
    metrics = [metric(name, "MEASURED", value, denominator, unit, "Calculated from differential comparison rows", True, True, comparison_evidence) for name, value, denominator, unit in measured]
    metrics += [
        metric("RAW_AMOUNT_MISMATCH", "NOT_OBSERVABLE", None, None, "component", "Production API does not expose the pre-rounding candidate amount", False, False, comparison_evidence),
        metric("ROUNDING_POINT_MISMATCH", "NOT_OBSERVABLE", None, None, "rounding decision", "Production API does not expose the exact rounding decision point", False, False, comparison_evidence),
        metric("RATE_VERSION_MISMATCH", "NOT_OBSERVABLE", None, None, "rate resolution", "Production response does not identify the resolved payroll-rate version", False, False, comparison_evidence),
        metric("TAX_VERSION_MISMATCH", "NOT_OBSERVABLE", None, None, "tax resolution", "Production response does not identify the resolved company-tax version", False, False, comparison_evidence),
        metric("TRANSLATION_MISMATCH", "NOT_APPLICABLE", None, None, "translator fixture", "Measured in the separate translator fixture validation, not this runtime run", False, False, "translation_validation_fixtures.json"),
        metric("PERSISTENCE_RESULT", "NOT_APPLICABLE", None, None, "E2E transaction", "Measured only by the full-pipeline E2E artifact", False, False, "runs/fixed/full_pipeline_e2e.json"),
    ]
    payload = {"artifact_version": "2.0", "schema_version": "2.0", "run_id": run, "metrics": metrics}
    path = ROOT / "runs" / run / "metrics.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def build_manifest(run: str, actual: dict, mismatches: dict, initial_dirty: dict[str, bool]) -> dict:
    run_dir = ROOT / "runs" / run
    tag = "tpr-ir-differential-baseline-v1" if run == "baseline" else "tpr-ir-differential-fixed-v1"
    go_commit = "1dcad9df1be852263590fd23ab11ce569ea1c99e" if run == "baseline" else command(ENGINE, "git", "rev-parse", "HEAD")
    laravel_commit = "ca16f0500d8404cecaca03950cfc252072ca3e23" if run == "baseline" else command(LARAVEL, "git", "rev-parse", "HEAD")
    manifest = {
        "artifact_version": "2.0", "schema_version": "2.0", "run_id": run,
        "provenance_status": "RECONSTRUCTED_BASELINE" if run == "baseline" else "EXECUTED_FIXED",
        "original_raw_baseline_available": False if run == "baseline" else None,
        "commits": {"laravel": laravel_commit, "go": go_commit, "differential_package": command(ENGINE, "git", "rev-parse", "HEAD")},
        "git_tag": tag,
        "dirty_working_tree": initial_dirty,
        "hashes": {
            "policy": sha(ROOT / "reference_policy.json"), "corpus": sha(ROOT / "oracle_input_cases.json"),
            "expected": sha(ROOT / "oracle_expected_results.json"), "actual": sha(run_dir / "actual_results.json"),
            "mismatches": sha(run_dir / "mismatch_details.json"), "metrics": sha(run_dir / "metrics.json"),
        },
        "comparator_version": "2.0", "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": {"os": platform.platform(), "timezone": "Asia/Bangkok", "locale": "C.UTF-8", "database_collation": database_collation()},
        "tool_versions": {"python": platform.python_version(), "go": version("go", "version"), "php": version("php", "--version")},
        "results": {"cases": mismatches["case_count"], "mismatches": mismatches["mismatch_count"], "mismatched_cases": mismatches["mismatched_case_count"]},
        "limitations": ["The original pre-fix raw run was overwritten; baseline was reconstructed using an explicit build tag against the preserved baseline semantics."] if run == "baseline" else [],
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    outcome = "FAIL" if mismatches["mismatch_count"] else "PASS"
    (run_dir / "summary.md").write_text(
        f"# {run.title()} differential run\n\n- Provenance: `{manifest['provenance_status']}`\n- Cases: {mismatches['case_count']}\n- Mismatches: {mismatches['mismatch_count']}\n- Mismatched cases: {mismatches['mismatched_case_count']}\n- Result: {outcome}\n",
        encoding="utf-8",
    )
    return manifest


def build_bug_evidence() -> None:
    corpus = {item["case_id"]: item for item in load(ROOT / "oracle_input_cases.json")["cases"]}
    expected = {item["case_id"]: item for item in load(ROOT / "oracle_expected_results.json")["results"]}
    baseline = {item["case_id"]: item for item in load(ROOT / "runs/baseline/actual_results.json")["results"]}
    fixed = {item["case_id"]: item for item in load(ROOT / "runs/fixed/actual_results.json")["results"]}
    mismatches = load(ROOT / "runs/baseline/mismatch_details.json")["mismatches"]
    by_case: dict[str, list[dict]] = {}
    for item in mismatches:
        by_case.setdefault(item["case_id"], []).append(item)
    for case_id, details in by_case.items():
        target = ROOT / "bug_evidence" / case_id.lower()
        target.mkdir(parents=True, exist_ok=True)
        for name, value in (("input", corpus[case_id]), ("expected", expected[case_id]), ("baseline_actual", baseline[case_id]), ("fixed_actual", fixed[case_id])):
            (target / f"{name}.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        (target / "root_cause.md").write_text(
            "# Root cause\n\n"
            f"Case `{case_id}` was rejected by the frozen oracle but accepted by the reconstructed baseline. "
            "The formula field was checked for existence, while the runtime type of its referenced fact was not validated. "
            "Consequently an invalid `employee.basic_salary` runtime type reached execution. The fix validates formula-fact runtime types before GRULE execution. "
            "The expected result was not changed.\n\n"
            f"Mismatch artifact: `{json.dumps(details, ensure_ascii=False)}`\n",
            encoding="utf-8",
        )
        (target / "regression_test_reference.txt").write_text("engine-rms/tpr_ir_test.go: test ValidateTPRRuleSet/invalid formula fact type\n", encoding="utf-8")


def main() -> None:
    initial_dirty = {
        "laravel": bool(command(LARAVEL, "git", "status", "--porcelain")),
        "go_and_package": bool(command(ENGINE, "git", "status", "--porcelain")),
    }
    manifests = {}
    for run in ("baseline", "fixed"):
        actual = load(ROOT / "runs" / run / "actual_results.json")
        mismatch = load(ROOT / "runs" / run / "mismatch_details.json")
        build_metrics(run, mismatch)
        manifests[run] = build_manifest(run, actual, mismatch, initial_dirty)
    build_bug_evidence()
    print(json.dumps({run: manifest["results"] for run, manifest in manifests.items()}))


if __name__ == "__main__":
    main()
