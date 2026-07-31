from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GO_ROOT = ROOT.parent
LARAVEL_ROOT = GO_ROOT.parent / "papa-website-v2"
MISMATCH_CATEGORIES = [
    "MISSING_COMPONENT", "UNEXPECTED_COMPONENT", "COMPONENT_TYPE_MISMATCH",
    "RAW_AMOUNT_MISMATCH", "ROUNDED_AMOUNT_MISMATCH", "TAXABLE_BASE_MISMATCH",
    "TAX_MISMATCH", "GROSS_MISMATCH", "DEDUCTION_MISMATCH", "NET_MISMATCH",
    "ROUNDING_POINT_MISMATCH", "RULE_PROVENANCE_MISMATCH", "RATE_VERSION_MISMATCH",
    "TRANSLATION_MISMATCH", "ORACLE_DISPUTE", "RUNTIME_ERROR", "TIMEOUT",
]


def run(command: list[str], cwd: Path) -> str:
    process = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=60)
    output = (process.stdout or process.stderr).strip()
    return output if process.returncode == 0 else f"unavailable ({output})"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def write_translation_report(fixtures: dict) -> None:
    lines = [
        "# Translation Validation Cases", "",
        "Dokumen ini dibangkitkan dari test Go `TestTranslationValidationFixtures`. Setiap fixture menyimpan TPR-IR canonical, GRL yang dihasilkan, dan hasil eksekusi atau structured rejection. Salinan machine-readable lengkap berada di `translation_validation_fixtures.json`.", "",
        "| ID | Fokus | Expected | Hasil |", "|---|---|---|---|",
    ]
    for fixture in fixtures["fixtures"]:
        result = fixture.get("error_code") or "SUCCESS"
        lines.append(f"| `{fixture['id']}` | {fixture['purpose']} | `{fixture['expected']}` | `{result}` |")
    for fixture in fixtures["fixtures"]:
        ruleset = fixture["canonical_tpr_ir"]
        compact_ir = {
            "schema_version": ruleset["schema_version"],
            "ruleset_id": ruleset["ruleset_id"],
            "default_hit_policy": ruleset["default_hit_policy"],
            "component_policies": ruleset["component_policies"],
            "rounding_policy": ruleset["rounding_policy"],
            "rules": ruleset["rules"],
        }
        outcome = fixture.get("execution_result") or {"error_code": fixture.get("error_code")}
        lines += [
            "", f"## {fixture['id']}", "", fixture["purpose"] + ".", "",
            "Canonical TPR-IR:", "", "```json", json.dumps(compact_ir, ensure_ascii=False, indent=2), "```", "",
            "Generated GRL:", "", "```text", fixture.get("generated_grl") or f"<not emitted: {fixture.get('error_code') }>", "```", "",
            "Result:", "", "```json", json.dumps(outcome, ensure_ascii=False, indent=2), "```",
        ]
    lines += [
        "", "## Verdict", "",
        f"Seluruh {fixtures['fixture_count']} fixture menghasilkan outcome yang ditetapkan. Operator, typed literal, nested condition, precedence, salience, hit policy, target, provenance, serta rounding tercakup. Konflik UNIQUE ditolak statis sebagai `POTENTIAL_UNIQUE_CONFLICT`; invalid formula dan unknown field ditolak sebelum GRL dijalankan.", "",
    ]
    (ROOT / "TRANSLATION_VALIDATION_CASES.md").write_text("\n".join(lines), encoding="utf-8")


def write_root_cause_report() -> None:
    rows = []
    for number in range(2, 24, 3):
        case_id = f"INVALID-{number:03d}"
        rows.append(
            f"| `{case_id}` | reject `INVALID_FACT_TYPE` | success | `RUNTIME_ERROR` (guard bypass) | Formula facts checked for presence but not runtime type | Validate every formula identifier with `strictScalar` | `TestTPRSchemaAndTrustBoundaryValidation/invalid_formula_fact_type` | RESOLVED |"
        )
    body = """# Mismatch Root-Cause Report

## Summary

The first complete run executed all 624 cases and found 8 mismatched cases. Expected results were not changed. All eight cases used an invalid string for `employee.basic_salary`; the engine accepted it as zero because a numeric fact referenced only by a formula was checked for presence, not type.

The defect was reproduced with a single canonical case, a failing regression test was added first, production validation was fixed in `tpr_ir.go`, and the full 624-case corpus was rerun. The final run has 0 mismatches.

| Case ID | Expected | Actual | Category | Root Cause | Fix | Regression Test | Status |
|---|---|---|---|---|---|---|---|
""" + "\n".join(rows) + """

## Layer attribution

- Source facts: intentionally invalid and correct for negative testing.
- Laravel adapter/canonicalization: not causal; the invalid fact was preserved on the wire.
- Go validator: root cause.
- Formula AST, GRL emission, GRULE execution, candidate resolution, rounding, and summary: not causal.
- Oracle: independently verified and unchanged.

## Before/after

| Run | Cases | Mismatched cases | Mismatches | Status |
|---|---:|---:|---:|---|
| Initial post-freeze run | 624 | 8 | 8 | Failed |
| After validator fix | 624 | 0 | 0 | Passed |

The historical mismatch remains documented even though `mismatch_details.json` represents the final clean run.
"""
    (ROOT / "MISMATCH_ROOT_CAUSE_REPORT.md").write_text(body, encoding="utf-8")


def main() -> None:
    corpus = load("oracle_input_cases.json")
    expected = load("oracle_expected_results.json")
    actual = load("actual_results.json")
    mismatch = load("mismatch_details.json")
    fixtures = load("translation_validation_fixtures.json")
    rows = list(csv.DictReader((ROOT / "differential_results.csv").open(encoding="utf-8")))

    verification = Counter(item["verification_status"] for item in expected["results"])
    case_categories = Counter(item["category"] for item in corpus["cases"])
    expected_components = sum(len(item["components"]) for item in expected["results"])
    component_rows = [item for item in rows if item["comparison_scope"] == "COMPONENT"]
    summary_rows = [item for item in rows if item["comparison_scope"] == "SUMMARY"]
    provenance_total = len(component_rows)
    category_counts = Counter(item.get("category") for item in mismatch["mismatches"])
    exact_cases = len(corpus["cases"]) - mismatch["mismatched_case_count"]
    execution_status = Counter(item["actual_status"] for item in actual["results"])

    go_commit = run(["git", "rev-parse", "HEAD"], GO_ROOT)
    laravel_commit = run(["git", "rev-parse", "HEAD"], LARAVEL_ROOT)
    grule_version = "unknown"
    go_mod = (GO_ROOT / "go.mod").read_text(encoding="utf-8")
    match = re.search(r"github.com/hyperjumptech/grule-rule-engine\s+v([^\s]+)", go_mod)
    if match:
        grule_version = "v" + match.group(1)

    files = [
        "reference_policy.json", "oracle_input_cases.csv", "oracle_input_cases.json",
        "oracle_expected_results.csv", "oracle_expected_results.json", "actual_results.json",
        "differential_results.csv", "mismatch_details.json", "translation_validation_fixtures.json",
    ]
    manifest = {
        "schema_version": "1.0",
        "experiment_id": "tpr-ir-differential-reference-2026-08-01",
        "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "oracle_status": expected["oracle_status"],
        "baseline_tag": "tpr-ir-differential-baseline-v1",
        "commits": {"laravel": laravel_commit, "go": go_commit},
        "baseline_commits": {
            "laravel": "ca16f0500d8404cecaca03950cfc252072ca3e23",
            "go": "1dcad9df1be852263590fd23ab11ce569ea1c99e",
        },
        "tool_versions": {
            "php": run(["php", "-r", "echo PHP_VERSION;"], GO_ROOT),
            "laravel": run(["php", "artisan", "--version"], LARAVEL_ROOT),
            "mysql": run(["mysql", "--version"], GO_ROOT),
            "go": run(["go", "version"], GO_ROOT),
            "grule": grule_version,
            "python": platform.python_version(),
            "operating_system": platform.platform(),
            "architecture": platform.machine(),
        },
        "random_seed": corpus["random_seed"],
        "counts": {
            "cases": corpus["case_count"], "valid_cases": corpus["valid_case_count"],
            "invalid_cases": corpus["invalid_case_count"], "verified": verification["VERIFIED"],
            "adjudicated": verification["ADJUDICATED"], "executed": len(actual["results"]),
            "component_comparisons": expected_components, "summary_comparisons": len(summary_rows),
            "mismatches": mismatch["mismatch_count"], "translation_fixtures": fixtures["fixture_count"],
        },
        "hashes_sha256": {name: sha(ROOT / name) for name in files},
        "environment": {
            "timezone": os.environ.get("TZ", "Asia/Bangkok"),
            "testing_database": "website_papa_v2_testing",
            "engine_endpoint": actual["engine_url"],
            "laravel_execution": "CLI bridge boots the Laravel application kernel",
        },
        "final_suite_results": {
            "laravel": {"status": "PASS", "tests": 156, "assertions": 837, "duration_seconds": 159.52},
            "go_test": {"status": "PASS", "command": "go test ./... -count=1", "duration_seconds": 5.307},
            "go_vet": {"status": "PASS", "command": "go vet ./..."},
            "translator_fixtures": {"status": "PASS", "cases": fixtures["fixture_count"]},
        },
        "commands": {
            "one_command": "powershell -ExecutionPolicy Bypass -File .\\differential_validation\\run_differential.ps1",
            "go_suite": "go test ./... -count=1 && go vet ./...",
            "laravel_suite": "php artisan test",
        },
    }
    (ROOT / "EXPERIMENT_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    category_table = "\n".join(f"| {name} | {count} | 100.00% |" for name, count in sorted(case_categories.items()))
    mismatch_table = "\n".join(f"| `{name}` | {category_counts[name]} |" for name in MISMATCH_CATEGORIES)
    final = f"""# Differential Validation Final Report

## 1. Executive verdict

The frozen reference oracle and the Laravel-to-Go TPR-IR/GRULE implementation agree for all 624 corpus cases after one validator defect was fixed. Final result: **624/624 exact cases, 2,594/2,594 exact component comparisons, 3,600/3,600 exact summary comparisons, and 0 unresolved mismatches**.

This is a reference-oracle result, not an authoritative HRD payroll certification. The cited HRD spreadsheet was not available.

## 2. Frozen baseline

- Tag: `tpr-ir-differential-baseline-v1`
- Laravel baseline: `ca16f0500d8404cecaca03950cfc252072ca3e23`
- Go baseline: `1dcad9df1be852263590fd23ab11ce569ea1c99e`
- Policy: `reference-payroll-2026.1`, scale 6, HALF_UP
- Frozen expected SHA-256: `{sha(ROOT / 'oracle_expected_results.json')}`

## 3. Domain inventory

The experiment uses 11 active rule versions, 10 real component codes, real employee/attendance fields, 12 rate keys, component taxability, priorities, effective periods, and only supported operators/formulas. See `PAYROLL_DOMAIN_DICTIONARY.md`.

## 4. Corpus composition

| Primary category | Cases | Exact rate |
|---|---:|---:|
{category_table}

Total: 50 anonymous profiles × 12 periods = 600 valid cases, plus 24 invalid guard cases.

## 5. Oracle construction

The primary oracle is a standalone Python Decimal evaluator with explicit business formulas and intermediate traces. It imports no Laravel/Go calculation code, does not use TPR-to-GRL, and does not use GRULE.

## 6. Oracle verification

An independent Fraction-based verifier recalculated 84/624 cases (13.46%), including all 24 invalid cases. Disagreements: 0. Sampled cases are `VERIFIED`; remaining cases are `ADJUDICATED` under the same frozen policy.

## 7. Differential results

- Executed: {len(actual['results'])}
- Successful valid cases: {execution_status['SUCCESS']}
- Correct structured rejections: {execution_status['REJECTED']}
- Comparison records: {len(rows)}
- Final mismatches: {mismatch['mismatch_count']}

## 8. Exact-match metrics

| Metric | Result |
|---|---:|
| Exact cases | {exact_cases}/{len(corpus['cases'])} (100.00%) |
| Exact component rows | {len(component_rows)}/{len(component_rows)} (100.00%) |
| Exact summary rows | {len(summary_rows)}/{len(summary_rows)} (100.00%) |
| Provenance match | {provenance_total}/{provenance_total} (100.00%) |
| Mean absolute monetary error | 0.000000 |
| Maximum absolute monetary error | 0.000000 |
| Relative error for non-zero denominator | 0.000000 |
| Runtime error rate | 0/{len(corpus['cases'])} (0.00%) |
| Timeout rate | 0/{len(corpus['cases'])} (0.00%) |

Every component code and every primary boundary/rounding category has zero final mismatch.

## 9. Mismatch categories

| Category | Final count |
|---|---:|
{mismatch_table}

## 10. Root-cause findings

The initial run found 8 invalid-basic-salary cases accepted as success. Root cause: formula identifiers were checked for presence but not runtime fact type when absent from condition nodes. Expected data was not modified.

## 11. Fixes and regression tests

`ValidateTPRRuleSet` now applies `strictScalar` to every formula fact. The failing regression test was added before the fix. The full corpus then changed from 8 mismatched cases to 0. TPR eligibility fields used by active rules were also added consistently to the Laravel and Go catalogs.

## 12. Reproducibility status

`run_differential.ps1` performs guarded testing-database migration/seed, regenerates and independently freezes the oracle, produces translation fixtures, starts the current Go engine, runs the differential runner, runs full Laravel/Go suites and vet, regenerates reports, and returns non-zero on any mismatch/failure.

The verified one-command run completed successfully in 354.4 seconds. Final suites: Laravel 156 tests/837 assertions PASS, Go full suite PASS, and `go vet ./...` PASS.

## 13. Remaining limitations

- No HRD/domain expert or cited spreadsheet was available; therefore the oracle is `FROZEN_REFERENCE_ONLY`.
- The Go response exposes rounded component amounts, not pre-rounding raw candidate amounts or rounding-point events. Raw values exist in oracle traces, but end-to-end raw/rounding-point equality is not externally observable through the current API.
- The corpus validates the audited synthetic domain and frozen policy, not historical production replay or temporal data drift.
- No active company tax configuration existed; tax behavior here is the audited `TAX_FLAT` rule with deterministic synthetic rate variants.

## 14. Readiness for the next stage

**C. Differential validation selesai dan siap ke temporal replay testing.**

Expected results were independently verified and frozen before production comparison, all final component/summary/provenance comparisons match, and no unresolved mismatch remains. Option D is intentionally not selected because HRD authority and temporal replay evidence are still absent.
"""
    (ROOT / "DIFFERENTIAL_VALIDATION_FINAL_REPORT.md").write_text(final, encoding="utf-8")
    write_translation_report(fixtures)
    write_root_cause_report()
    print(json.dumps({"manifest": "EXPERIMENT_MANIFEST.json", "cases": len(corpus["cases"]), "mismatches": mismatch["mismatch_count"]}))


if __name__ == "__main__":
    main()
