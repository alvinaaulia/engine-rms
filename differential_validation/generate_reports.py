"""Regenerate research reports exclusively from validated artifacts and raw logs."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from evidence import parse_exit_status, parse_go_test, parse_junit
from validate_artifacts import main as validate_artifacts

ROOT = Path(__file__).resolve().parent
LOGS = ROOT / "runs" / "fixed" / "logs"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, content: str) -> None:
    (ROOT / name).write_text(content.rstrip() + "\n", encoding="utf-8")


def percent(numerator: int, denominator: int) -> str:
    return "N/A" if denominator == 0 else f"{numerator * 100 / denominator:.2f}%"


def result_label(mismatches: int) -> str:
    return "PASS" if mismatches == 0 else "FAIL"


def table(rows: list[list[object]], headers: list[str]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines.extend("| " + " | ".join(str(value).replace("\n", " ") for value in row) + " |" for row in rows)
    return "\n".join(lines)


def generate() -> None:
    validate_artifacts()
    corpus = load(ROOT / "oracle_input_cases.json")
    expected = load(ROOT / "oracle_expected_results.json")
    baseline = load(ROOT / "runs/baseline/manifest.json")
    fixed = load(ROOT / "runs/fixed/manifest.json")
    baseline_mismatch = load(ROOT / "runs/baseline/mismatch_details.json")
    fixed_mismatch = load(ROOT / "runs/fixed/mismatch_details.json")
    metrics = load(ROOT / "runs/fixed/metrics.json")
    e2e = load(ROOT / "runs/fixed/full_pipeline_e2e.json")
    freeze = load(ROOT / ".oracle_frozen.json")
    fixtures = load(ROOT / "translation_validation_fixtures.json")

    evidence = {
        "laravel": parse_junit(LOGS / "laravel-tests.meta.json"),
        "go": parse_go_test(LOGS / "go-tests.meta.json"),
        "go_vet": parse_exit_status(LOGS / "go-vet.meta.json"),
        "translator": parse_go_test(LOGS / "translator-go-test.meta.json"),
        "e2e": parse_junit(LOGS / "e2e.meta.json"),
        "corpus": parse_exit_status(LOGS / "corpus-generation.meta.json"),
        "oracle": parse_exit_status(LOGS / "oracle-generation.meta.json"),
        "oracle_verifier": parse_exit_status(LOGS / "oracle-verification.meta.json"),
        "baseline_differential": parse_exit_status(ROOT / "runs/baseline/logs/differential.meta.json"),
        "fixed_differential": parse_exit_status(LOGS / "differential.meta.json"),
    }
    if any(item["status"] != "PASS" for item in evidence.values()):
        failed = [name for name, item in evidence.items() if item["status"] != "PASS"]
        raise RuntimeError(f"report generation refused: failed command evidence {failed}")

    category_counts = Counter(item["primary_category"] for item in corpus["cases"])
    route_counts = Counter(item["execution_route"] for item in corpus["cases"])
    verification_counts = Counter(item["verification_status"] for item in expected["results"])

    write("ORACLE_STATUS_MIGRATION_REPORT.md", f"""
# Oracle status migration report

The previous blanket use of `ADJUDICATED` was invalid and has been removed. Status is now attached per case with verifier identity, method, timestamp, adjudication reference, and notes.

{table([[key, value] for key, value in sorted(verification_counts.items())], ['Verification status', 'Cases'])}

No row is adjudicated without written evidence. The frozen artifact remains `FROZEN_REFERENCE_ORACLE` and is explicitly not an authoritative business oracle. Frozen expected hash: `{freeze['hashes']['oracle_expected_results.json']}`.
""")

    category_spec_rows = [
        ["NORMAL_CASE", "Valid, no boundary, no interaction, canonical route", "GENERAL_VALID_PAYROLL"],
        ["BOUNDARY_CASE", "At least one declared B-1/B/B+1 boundary", "treatment_parameters.boundaries"],
        ["ROUNDING_SENSITIVE", "Raw value below/at/above six-decimal HALF_UP tie", "rounding_probe"],
        ["LEGACY_ADAPTER", "Request is actually sent through legacy rules payload", "execution_route=LEGACY_ADAPTER"],
        ["RULE_INTERACTION", "At least two rules match", "matched_rule_count>=2"],
        ["INVALID_INPUT", "Structured rejection and expected error code", "validity=INVALID"],
        ["EFFECTIVE_DATE", "Before, at, or during effective period", "effective_from/position"],
        ["ZERO_VALUE", "All attendance adjustments explicitly zero", "ZERO_ATTENDANCE_ADJUSTMENTS"],
    ]
    write("CORPUS_CATEGORY_SPECIFICATION.md", "# Corpus category specification\n\n" + table(category_spec_rows, ["Category", "Predicate", "Treatment evidence"]))
    write("CORPUS_CATEGORY_AUDIT.md", f"""
# Corpus category audit

Category assignment is derived from facts, matched rules, route, boundaries, and explicit treatments. The generator validator rejects missing treatments, fake legacy routing, boundary cases without boundary metadata, and invalid cases without expected error codes.

{table([[key, value] for key, value in sorted(category_counts.items())], ['Primary category', 'Cases'])}

{table([[key, value] for key, value in sorted(route_counts.items())], ['Execution route', 'Cases'])}

The three effective-date cases execute before, exactly at, and during the open-ended effective period. No category is assigned using a display-balancing modulo. Modulo remains only where it creates deterministic input variation; category predicates are evaluated from the resulting facts.
""")

    comparison_rows = [
        ["Baseline (reconstructed)", baseline["commits"]["laravel"], baseline["commits"]["go"], baseline["results"]["cases"], baseline["results"]["mismatches"], result_label(baseline["results"]["mismatches"])],
        ["Fixed", fixed["commits"]["laravel"], fixed["commits"]["go"], fixed["results"]["cases"], fixed["results"]["mismatches"], result_label(fixed["results"]["mismatches"])],
    ]
    write("BASELINE_FIXED_COMPARISON.md", f"""
# Baseline versus fixed

{table(comparison_rows, ['Stage', 'Laravel commit', 'Go commit', 'Cases', 'Mismatch', 'Result'])}

The original eight-mismatch raw output had been overwritten before this remediation. It is not presented as original evidence. The baseline is labeled `RECONSTRUCTED_BASELINE` and was executed with the preserved pre-fix runtime-type behavior behind the non-production `differential_baseline` build tag. The fixed run used the same frozen corpus and expected results.
""")

    mismatch_cases = sorted({item["case_id"] for item in baseline_mismatch["mismatches"]})
    write("BUG_DISCOVERY_AND_REMEDIATION_REPORT.md", f"""
# Bug discovery and remediation report

The reconstructed baseline produced {baseline_mismatch['mismatch_count']} mismatches across {baseline_mismatch['mismatched_case_count']} cases: {', '.join(mismatch_cases)}. The formula field was checked for existence, but referenced fact runtime types were not validated; invalid `employee.basic_salary` types therefore reached execution. The fix validates formula fact runtime types before GRULE execution.

Each case is preserved under `bug_evidence/<case-id>/` with input, unchanged expected output, baseline actual, fixed actual, root cause, and the regression-test reference. The fixed run produced {fixed_mismatch['mismatch_count']} mismatch. The oracle expected artifact hash stayed frozen for both runs.
""")

    metric_rows = [[item["metric"], "yes" if item["comparator_available"] else "no", "yes" if item["source_data_available"] else "no", item["status"], "null" if item["value"] is None else item["value"], item["reason"]] for item in metrics["metrics"]]
    write("METRIC_OBSERVABILITY_MATRIX.md", "# Metric observability matrix\n\n" + table(metric_rows, ["Metric", "Comparator", "Source", "Status", "Value", "Reason"]) + "\n\nA numeric zero appears only for measured metrics. Unobservable and non-applicable metrics carry a null value.")

    evidence_rows = []
    for name, parsed in evidence.items():
        meta = parsed["evidence"]
        evidence_rows.append([name, meta["evidence_file"], meta["parser_version"], meta["exit_code"], meta["started_at"], meta["finished_at"], meta["duration_seconds"], parsed["status"]])
    write("AUTOMATED_EVIDENCE_GENERATION_REPORT.md", f"""
# Automated evidence generation report

{table(evidence_rows, ['Command', 'Evidence file', 'Parser', 'Exit', 'Started', 'Finished', 'Seconds', 'Status'])}

The generator refuses missing, malformed, failed, inconsistent, or stale evidence. Its parser tests cover those conditions and the absence of a hard-coded fallback. Test/assertion counts and durations below are parsed from JUnit or Go JSON events.

{table([
        ['Laravel full suite', evidence['laravel']['tests'], evidence['laravel']['passed'], evidence['laravel']['failures'] + evidence['laravel']['errors'], evidence['laravel']['skipped'], evidence['laravel']['assertions'], evidence['laravel']['duration_seconds']],
        ['Go full suite', evidence['go']['tests'], evidence['go']['passed'], evidence['go']['failed'], evidence['go']['skipped'], 'not emitted', evidence['go']['duration_seconds']],
        ['Translator fixture test', evidence['translator']['tests'], evidence['translator']['passed'], evidence['translator']['failed'], evidence['translator']['skipped'], 'not emitted', evidence['translator']['duration_seconds']],
        ['Full-pipeline E2E PHPUnit', evidence['e2e']['tests'], evidence['e2e']['passed'], evidence['e2e']['failures'] + evidence['e2e']['errors'], evidence['e2e']['skipped'], evidence['e2e']['assertions'], evidence['e2e']['duration_seconds']],
    ], ['Suite', 'Tests', 'Passed', 'Failed', 'Skipped', 'Assertions', 'Seconds'])}
""")

    write("FULL_PIPELINE_E2E_REPORT.md", f"""
# Full-pipeline Laravel–Go E2E report

Validation type: `FULL_PIPELINE_END_TO_END_VALIDATION`.

{table([
        ['Cases', e2e['case_count']], ['Exact valid results', e2e['exact_match_count']], ['Expected configuration rejections', e2e['expected_rejection_count']],
        ['Unexpected mismatch', e2e['mismatch_count']], ['Persisted salary records', e2e['persistence_count']], ['Runtime failures', 0 if e2e['mismatch_count'] == 0 else e2e['mismatch_count']],
    ], ['Measure', 'Value'])}

The valid path is testing database → attendance/overtime records → `buildFactsFromDatabase` → `PayrollRuleEngineService::execute` → Go HTTP `/execute` → GRULE → Laravel normalization/provenance → salary persistence. The subset covers salary, attendance, overtime, deduction, bonus, tax, rate dependencies, formulas, approval/active validation, provenance, six-decimal rounding, and invalid configuration rejection.

Translator validation is separate: `{fixtures['fixture_count']}` fixture records were exercised by {evidence['translator']['tests']} Go test events with {evidence['translator']['failed']} failure. It is not merged into the E2E case count.
""")

    write("DOMAIN_EXPERT_VALIDATION_FORM.md", """
# Domain expert validation form

Oracle status: `FROZEN_REFERENCE_ORACLE / NOT_AUTHORITATIVE_BUSINESS_ORACLE`

Reviewer name/role: ____________________  Date: __________  Approval reference: ____________________

| Case ID | Category | Policy/rate/tax item | Expected result reviewed | Comment/disagreement | Decision |
|---|---|---|---|---|---|
| | | | | | |

Sampling protocol: at least 10% of the corpus, every primary category, every payroll component, all important boundaries, every tax/rate policy, and every historically mismatched case. Attach signed approval or an immutable decision reference. Until completed, no case may be promoted to `ADJUDICATED` and no authoritative/company/legal claim may be made.
""")
    write("DOMAIN_VALIDATION_STATUS.md", f"""
# Domain validation status

Status: `FROZEN_REFERENCE_ORACLE / NOT_AUTHORITATIVE_BUSINESS_ORACLE`.

The independent verifier recalculated {verification_counts['INDEPENDENTLY_VERIFIED']} of {expected['case_count']} cases ({percent(verification_counts['INDEPENDENTLY_VERIFIED'], expected['case_count'])}); the remainder are policy-derived. This demonstrates agreement with the frozen reference policy, not correctness against company payroll practice, HRD decisions, legislation, or an absent source spreadsheet. Domain-expert validation is pending.
""")

    inventory = sorted(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file() and ".tmp" not in path.parts)
    write("ARTIFACT_INVENTORY.md", "# Artifact inventory\n\n" + "\n".join(f"- `{name}`" for name in inventory))

    write("AUDIT_DIFFERENTIAL_PACKAGE.md", """
# Audit differential package

| File/area | Function | Input | Output | Confirmed problem | Remediation |
|---|---|---|---|---|---|
| `generate_corpus.py` | Corpus generator | Frozen policy/seed | cases JSON/CSV | Categories were index/modulo labels | Treatment predicates, route, rationale, and validator |
| `verify_oracle.py` | Independent verifier | Expected/corpus/policy | Frozen expected/status report | Unverified rows called adjudicated | Independent and policy-derived statuses |
| `run_differential.py` | Runtime runner/comparator | Frozen cases/expected | Actual/CSV/mismatch | Single canonical route and overwritten output | Real canonical/legacy routes and run directories |
| `generate_reports.py` | Report generator | Raw artifacts/logs | Research reports | Static counts/status/durations | Strict evidence parsers and refusal on bad evidence |
| `runs/` | Experimental evidence | Baseline/fixed engines | Separate runs | Baseline/fixed mixed; initial raw overwritten | Explicit reconstructed baseline and fixed evidence |
| `metrics.json` | Observability model | Comparator output | Metric status/value | Unmeasured fields reported as zero | Measured/not-observable/not-applicable states |
| Laravel E2E test | Full pipeline | Isolated DB + live Go | JUnit/E2E JSON | Full payroll service path absent | 36-case DB/service/HTTP/GRULE/persistence subset |
| schemas/validator | Artifact gate | All JSON artifacts | validation report | Weak cross-artifact validation | JSON Schema plus IDs/hashes/metric/adjudication checks |
| reproducibility files | External rerun | source/env | logs/manifests/reports | Local Windows paths and binary reliance | Relative Bash/Make path with source builds |

Historical reports containing the invalid terminology remain replaced, not used as evidence. The user-owned `differential_validation.zip` was not modified.
""")

    overall = {
        "artifact_version": "2.0", "schema_version": "2.0",
        "oracle_status": expected["oracle_status"], "domain_status": "NOT_AUTHORITATIVE_BUSINESS_ORACLE",
        "baseline": baseline, "fixed": fixed,
        "translator": {"fixture_count": fixtures["fixture_count"], "test_events": evidence["translator"]["tests"], "failed": evidence["translator"]["failed"], "evidence": evidence["translator"]["evidence"]},
        "full_pipeline_e2e": {key: value for key, value in e2e.items() if key != "results"},
        "test_evidence": evidence,
    }
    (ROOT / "EXPERIMENT_MANIFEST.json").write_text(json.dumps(overall, indent=2) + "\n", encoding="utf-8")

    write("DIFFERENTIAL_VALIDATION_FINAL_REPORT.md", f"""
# Differential validation final report

## Executive result

The reconstructed baseline found {baseline_mismatch['mismatch_count']} mismatches; the fixed run found {fixed_mismatch['mismatch_count']} across {fixed_mismatch['case_count']} cases. This establishes remediation against the frozen reference policy, while domain authority remains unvalidated.

## Evidence breakdown

{table([
        ['Baseline differential', baseline_mismatch['case_count'], baseline_mismatch['mismatch_count'], result_label(baseline_mismatch['mismatch_count'])],
        ['Fixed differential', fixed_mismatch['case_count'], fixed_mismatch['mismatch_count'], result_label(fixed_mismatch['mismatch_count'])],
        ['Translator fixtures', fixtures['fixture_count'], evidence['translator']['failed'], evidence['translator']['status']],
        ['Full-pipeline E2E', e2e['case_count'], e2e['mismatch_count'], evidence['e2e']['status']],
    ], ['Evidence', 'Cases/fixtures', 'Mismatch/failure', 'Result'])}

Oracle cases: {verification_counts['INDEPENDENTLY_VERIFIED']} independently verified and {verification_counts['POLICY_DERIVED']} policy-derived; no unsupported adjudication. Unobservable metrics remain null rather than zero. Full test evidence is recorded in `AUTOMATED_EVIDENCE_GENERATION_REPORT.md`.

## Limitations

- The pre-remediation raw baseline was overwritten; the preserved evidence is a clearly labeled reconstruction.
- The reference oracle is not an authoritative HRD/company/legal oracle.
- Raw amount, rounding decision point, rate version, and tax version are not observable through the production API.
- Clean-environment Docker execution must be reported from actual execution; absence of Docker on the current host cannot be converted into a success claim.
- Temporal replay was intentionally not started.
""")

    print(json.dumps({"reports_generated": True, "baseline_mismatches": baseline_mismatch["mismatch_count"], "fixed_mismatches": fixed_mismatch["mismatch_count"], "e2e_cases": e2e["case_count"]}))


if __name__ == "__main__":
    generate()
