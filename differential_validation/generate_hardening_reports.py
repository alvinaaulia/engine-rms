"""Generate evidence-hardening reports only from validated structured artifacts."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from evidence import parse_exit_status, parse_go_test, parse_junit

ROOT = Path(__file__).resolve().parent


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def write(name: str, body: str) -> None:
    (ROOT / name).write_text(body.rstrip() + "\n", encoding="utf-8")


def table(headers: list[str], rows: list[list[object]]) -> str:
    rendered = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    rendered.extend("| " + " | ".join(str(value).replace("\n", " ") for value in row) + " |" for row in rows)
    return "\n".join(rendered)


def evidence() -> dict:
    hard = ROOT / "runs/hardening/raw-logs"
    return {
        "Laravel full suite": parse_junit(hard / "laravel-tests-hardening.meta.json"),
        "Go full suite": parse_go_test(hard / "go-tests-hardening.meta.json"),
        "Go vet": parse_exit_status(hard / "go-vet-hardening.meta.json"),
        "Translator fixtures": parse_go_test(hard / "translator-hardening.meta.json"),
        "Laravel E2E suite": parse_junit(ROOT / "runs/fixed/raw-logs/e2e-hardening.meta.json"),
        "Corpus generation": parse_exit_status(hard / "corpus-generation.meta.json"),
        "Oracle generation": parse_exit_status(hard / "oracle-generation.meta.json"),
        "Oracle verification": parse_exit_status(hard / "oracle-verification.meta.json"),
        "Reconstructed baseline repeat 1": parse_exit_status(ROOT / "runs/reconstructed-baseline/repeat-1/raw-logs/differential.meta.json"),
        "Reconstructed baseline repeat 2": parse_exit_status(ROOT / "runs/reconstructed-baseline/repeat-2/raw-logs/differential.meta.json"),
        "Fixed differential": parse_exit_status(ROOT / "runs/fixed/raw-logs/differential-hardening.meta.json"),
    }


def generate() -> dict:
    frozen = load("FROZEN_EVIDENCE_BASELINE.json")
    working = load("working-tree-audit.json")
    inventory = load("ARTIFACT_INVENTORY.json")
    baseline = load("runs/reconstructed-baseline/manifest.json")
    baseline_actual = load("runs/reconstructed-baseline/actual-results.json")
    baseline_mismatch = load("runs/reconstructed-baseline/mismatch-details.json")
    fixed_state = load("runs/fixed/source-state.json")
    fixed_actual = load("runs/fixed/actual_results.json")
    fixed_mismatch = load("runs/fixed/mismatch_details.json")
    expected = load("oracle_expected_results.json")
    fixtures = load("translation_validation_fixtures.json")
    traces = load("e2e-execution-traces.json")
    metrics = load("metric-results.json")
    reproduction = load("REPRODUCIBILITY_MANIFEST.json")
    commands = evidence()
    if any(value["status"] != "PASS" for value in commands.values()):
        raise RuntimeError("hardening report refused because command evidence is not PASS")

    verification = Counter(row["verification_status"] for row in expected["results"])
    categories = Counter(row["evaluation_category"] for row in traces["traces"])
    persisted = sum(bool(row["persistence_asserted"]) for row in traces["traces"])
    invalid_guards = categories["LARAVEL_CONFIGURATION_GUARD"]
    full_pipeline = categories["FULL_PAYROLL_PIPELINE"]
    baseline_cases = len(baseline_actual["results"])
    fixed_cases = len(fixed_actual["results"])
    baseline_mismatches = baseline_mismatch["mismatch_count"]
    fixed_mismatches = fixed_mismatch["mismatch_count"]
    unsupported_adjudication = verification["ADJUDICATED"]

    layers = [
        {"layer": "Reconstructed baseline differential", "cases": baseline_cases, "unit": "corpus case", "mismatch": baseline_mismatches, "result": "RECONSTRUCTED_MISMATCH_REPRODUCED", "evidence": "runs/reconstructed-baseline/manifest.json"},
        {"layer": "Fixed differential", "cases": fixed_cases, "unit": "corpus case", "mismatch": fixed_mismatches, "result": "PASS" if fixed_mismatches == 0 else "FAIL", "evidence": "runs/fixed/mismatch_details.json"},
        {"layer": "Translator fixtures", "cases": fixtures["fixture_count"], "unit": "translator fixture", "mismatch": commands["Translator fixtures"]["failed"], "result": commands["Translator fixtures"]["status"], "evidence": "runs/hardening/raw-logs/translator-hardening.meta.json"},
        {"layer": "Laravel-to-Go / full payroll pipeline", "cases": full_pipeline, "unit": "payroll transaction", "mismatch": sum(row["expected_hash"] != row["actual_hash"] for row in traces["traces"] if row["evaluation_category"] == "FULL_PAYROLL_PIPELINE"), "result": commands["Laravel E2E suite"]["status"], "evidence": "e2e-execution-traces.json"},
        {"layer": "Persistence E2E", "cases": persisted, "unit": "persisted payroll transaction", "mismatch": sum(not row["persistence_asserted"] for row in traces["traces"] if row["evaluation_category"] == "FULL_PAYROLL_PIPELINE"), "result": commands["Laravel E2E suite"]["status"], "evidence": "e2e-execution-traces.json"},
        {"layer": "Laravel configuration guards", "cases": invalid_guards, "unit": "rejected configuration", "mismatch": sum(row["expected_hash"] != row["actual_hash"] for row in traces["traces"] if row["evaluation_category"] == "LARAVEL_CONFIGURATION_GUARD"), "result": commands["Laravel E2E suite"]["status"], "evidence": "e2e-execution-traces.json"},
    ]

    final_data = {
        "artifact_version": "2.0",
        "evaluation_layers": layers,
        "oracle": {"total": expected["case_count"], "independently_verified": verification["INDEPENDENTLY_VERIFIED"], "policy_derived": verification["POLICY_DERIVED"], "unsupported_adjudication": unsupported_adjudication},
        "baseline": {"type": baseline["baseline_type"], "repeat_count": len(baseline["repeat_runs"]), "stable_mismatch_case_ids": baseline["stable_mismatch_case_ids"], "corpus_hash": baseline["corpus_hash"], "expected_hash": baseline["expected_hash"], "policy_hash": baseline["policy_hash"]},
        "fixed": {"source_commit": fixed_state["source_commit"], "mismatch_count": fixed_mismatches, "corpus_hash": fixed_state["corpus_hash"], "expected_hash": fixed_state["expected_hash"], "policy_hash": fixed_state["policy_hash"]},
        "e2e": {"suite_cases": traces["case_count"], "full_pipeline_cases": full_pipeline, "configuration_guard_cases": invalid_guards, "persistence_cases": persisted},
        "clean_environment": {"status": reproduction["status"], "exit_code": reproduction["exit_code"], "missing_dependencies": reproduction["missing_dependencies"]},
        "domain_status": "DOMAIN_VALIDATION_PENDING",
        "temporal_replay": "NOT_STARTED",
        "hardening_source": frozen["hardening_source"],
        "command_evidence": {name: value for name, value in commands.items()},
    }
    write("final-report-data.json", json.dumps(final_data, ensure_ascii=False, indent=2))

    versions = frozen["versions"]
    write("FROZEN_EVIDENCE_BASELINE.md", f"""
# Frozen evidence baseline

The pre-hardening source state is frozen independently from later evidence-hardening edits.

{table(['Repository', 'Commit', 'Branch', 'Tag', 'Initial status'], [
    ['engine-rms / differential package', frozen['engine']['commit'], frozen['engine']['branch'], frozen['engine']['fixed_source_tag'], 'clean'],
    ['papa-website-public', frozen['laravel']['commit'], frozen['laravel']['branch'], frozen['laravel']['tag'], 'clean'],
])}

{table(['Runtime', 'Observed value'], [[key, value if value is not None else 'NOT_AVAILABLE'] for key, value in versions.items()])}

Structured source: `FROZEN_EVIDENCE_BASELINE.json`. The final fixed source is separately bound in `runs/fixed/source-state.json`; this document does not rewrite the historical freeze after hardening changes.

Evidence-hardening source/test tag: `{frozen['hardening_source']['tag']}` at engine/package commit `{frozen['hardening_source']['engine_and_package_commit']}` and Laravel test commit `{frozen['hardening_source']['laravel_test_commit']}`.
""")

    change_counts = Counter(row["category"] for row in working["current_changes"])
    write("WORKING_TREE_AUDIT.md", f"""
# Working-tree audit

Captured at `{working['captured_at']}`. The workspace became dirty only after the frozen state while tests, pipeline code, and generated evidence were hardened.

{table(['Classification', 'Files'], [[name, count] for name, count in sorted(change_counts.items())])}

The complete path-level inventory is `working-tree-audit.json`. User-owned archive files and unrelated existing files were not rewritten.
""")

    with (ROOT / "EVIDENCE_CLAIM_MATRIX.csv").open(encoding="utf-8", newline="") as handle:
        claim_rows = list(csv.DictReader(handle))
    write("EVIDENCE_INTEGRITY_AUDIT.md", f"""
# Evidence integrity audit

{table(['Claim', 'Value', 'Evidence', 'Status'], [[row.get('claim'), row.get('value'), row.get('evidence_file'), row.get('status')] for row in claim_rows])}

- Inventoried files: {inventory['file_count']} (structured source: `ARTIFACT_INVENTORY.json`).
- Duplicate case IDs, frozen hashes, per-case hashes, manifest hashes, metric nullability, E2E paths, command exit evidence, and report counts are enforced by `validate_artifacts.py`.
- Reconstructed evidence is never labeled original. A command is PASS only when its recorded exit code and parsed result support PASS.
""")

    write("REPORT_GENERATOR_AUDIT.md", f"""
# Report generator audit

The reporting chain parses raw command metadata, JUnit XML, and Go JSON events; validates schemas and hashes; derives counts from artifacts; writes `final-report-data.json`; and rejects report/artifact count disagreement. No fallback PASS, test count, mismatch count, assertion count, or duration is used.

{table(['Evidence parser', 'Tests', 'Failed', 'Exit', 'Duration seconds', 'Raw metadata'], [[name, value.get('tests', 'N/A'), value.get('failed', value.get('failures', 'N/A')), value['evidence']['exit_code'], value['evidence']['duration_seconds'], value['evidence']['evidence_file']] for name, value in commands.items()])}

Regression tests cover missing evidence, malformed JSON/logs, duplicate IDs, hash mismatch, stale metadata, failed tests, missing exit code, manual PASS, invalid metric nullability, unsupported adjudication, incomplete E2E paths, false ORIGINAL baselines, and inconsistent report counts.
""")

    write("BASELINE_RECONSTRUCTION_PROVENANCE.md", f"""
# Baseline reconstruction provenance

Baseline type: `{baseline['baseline_type']}`. Original historical raw output is unavailable. The fixed source was rebuilt with the non-production `differential_baseline` tag, which disables only the remediated runtime type check. The reconstruction was run {len(baseline['repeat_runs'])} times and reproduced {baseline_mismatches} stable mismatching case IDs: {', '.join(baseline['stable_mismatch_case_ids'])}.

{table(['Repeat', 'Mismatch', 'Semantic result hash', 'Raw command evidence'], [[index + 1, row['mismatch_count'], row['semantic_results_hash'], row['command_evidence']] for index, row in enumerate(baseline['repeat_runs'])])}

Corpus, expected-result, and policy hashes are `{baseline['corpus_hash']}`, `{baseline['expected_hash']}`, and `{baseline['policy_hash']}`. Method, limitations, patch, and source state are in `runs/reconstructed-baseline/`.
""")

    trace_rows = [[name, count] for name, count in sorted(categories.items())]
    write("FULL_PIPELINE_E2E_AUDIT.md", f"""
# Full-pipeline E2E audit

The suite contains {traces['case_count']} traces, but the evidence supports {full_pipeline} true full-payroll transactions and {invalid_guards} Laravel configuration guards. The guards terminate before HTTP and are not cosmetically counted as full pipeline.

{table(['Evaluation category', 'Cases'], trace_rows)}

Each full-pipeline trace records testing database fixtures, `buildFactsFromDatabase`, `PayrollRuleEngineService::execute`, Go `/execute`, GRULE, normalization, component hashes, salary persistence, and database assertion. Go request IDs remain `NOT_OBSERVABLE`; request/response hashes provide the available correlation evidence.
""")
    write("FULL_PIPELINE_E2E_REPORT.md", f"""
# Laravel-Go E2E report

{table(['Category', 'Cases', 'Persistence asserted', 'Hash mismatch', 'Evidence'], [
    ['FULL_PAYROLL_PIPELINE', full_pipeline, persisted, layers[3]['mismatch'], 'e2e-execution-traces.json'],
    ['LARAVEL_CONFIGURATION_GUARD', invalid_guards, 0, layers[5]['mismatch'], 'e2e-execution-traces.json'],
])}

Translator fixtures are reported separately and are not included in either E2E category.
""")

    write("ORACLE_VERIFICATION_AUDIT.md", f"""
# Oracle verification audit

{table(['Verification status', 'Cases'], [[name, count] for name, count in sorted(verification.items())])}

Every expected case carries verification method, verifier ID where independently verified, timestamp where applicable, expected hash, policy hash, and notes. Unsupported adjudication count is {unsupported_adjudication}. The independent verifier is a standalone reference-policy calculator and does not import production Go, GRULE, or translator code. This remains a frozen reference oracle, not an authoritative payroll oracle.
""")

    metric_rows = [[row['metric'], row['status'], row['value'], row['denominator'], row['unit'], row['reason'], row['evidence_file']] for row in metrics['metrics']]
    write("METRIC_OBSERVABILITY_MATRIX.md", "# Metric observability matrix\n\n" + table(['Metric', 'Status', 'Value', 'Denominator', 'Unit', 'Reason', 'Evidence'], metric_rows) + "\n\nNon-measured and unobservable values remain null; zero is used only for measured quantities.")

    write("CLEAN_ENVIRONMENT_EXECUTION_REPORT.md", f"""
# Clean-environment execution report

Status: `{reproduction['status']}`. Exit code: `{reproduction['exit_code']}`. Missing dependencies: {', '.join(reproduction['missing_dependencies']) or 'none'}.

The intended method is `{reproduction['clean_environment_method']}` with `{reproduction['planned_command']}`. No build log, container version, runtime timestamps, or peak-memory value is fabricated. Docker was not available on this host, so clean-environment reproduction is not a PASS.
""")

    write("CODE_CHANGE_REPORT.md", f"""
# Code change report

Evidence hardening changed oracle provenance fields, schema validation, strict report generation, reproducibility runners, and Laravel E2E trace capture. The Laravel change is test-only. Production payroll remediation remains the runtime formula-fact type validation recorded by `runs/reconstructed-baseline/remediation-revert.patch` and the per-case regression references under `bug-evidence/`.

The current path-level classifications ({sum(change_counts.values())} files) are retained in `working-tree-audit.json`; generated evidence is separated from source and test changes. Hardening code is tagged `{frozen['hardening_source']['tag']}`. Temporal replay was not added or started.
""")

    write("AUTOMATED_EVIDENCE_GENERATION_REPORT.md", f"""
# Automated evidence generation report

{table(['Command', 'Status', 'Tests', 'Passed', 'Failed', 'Assertions', 'Duration seconds', 'Exit', 'Evidence'], [[name, value['status'], value.get('tests', 'N/A'), value.get('passed', 'N/A'), value.get('failed', value.get('failures', 'N/A')), value.get('assertions', 'N/A'), value['evidence']['duration_seconds'], value['evidence']['exit_code'], value['evidence']['evidence_file']] for name, value in commands.items()])}

All values above are parsed from raw metadata/logs. Generator and validator unit tests are executed separately by the one-command runner and must exit zero before report generation.
""")

    layer_table = table(['Evaluation layer', 'Cases', 'Measured unit', 'Mismatch', 'Result', 'Evidence'], [[row['layer'], row['cases'], row['unit'], row['mismatch'], row['result'], row['evidence']] for row in layers])
    write("DIFFERENTIAL_VALIDATION_FINAL_REPORT_V2.md", f"""
# Differential validation final report V2

## Executive verdict

The fixed implementation agrees with the frozen reference oracle across {fixed_cases} differential cases. The reconstructed pre-remediation behavior reproducibly yields {baseline_mismatches} mismatches. Evidence hardening is locally verified, but clean-environment reproduction is `{reproduction['status']}` and domain validation is pending.

## Evaluation layers

{layer_table}

## Claims supported

- Fixed/reference exact agreement for the measured differential cases.
- A clearly labeled reconstructed baseline reproduced the stable mismatch set in {len(baseline['repeat_runs'])} executions.
- Independently verified and policy-derived oracle cases are separated per case.
- Translator, full payroll pipeline, persistence, and Laravel-only configuration guards are reported separately.

## Claims not supported

- No original historical baseline raw output is claimed.
- The reference oracle is not authoritative HRD, organizational, legal, or statutory evidence.
- Clean-container reproduction is not claimed as PASS.
- The {invalid_guards} pre-HTTP configuration guards are not called full-payroll pipeline executions.

## Reconstructed evidence

`runs/reconstructed-baseline/` contains the method, source state, remediation patch, two runs, stable semantic hashes, and limitations.

## Original evidence

Current fixed raw logs, source hashes, corpus, frozen expected results, policy, test logs, and per-case E2E traces are retained. The unavailable historical raw baseline is explicitly excluded.

## Unobservable metrics

See `metric-results.json`; unobservable values are null with reasons and no false zero.

## Domain validity limitation

Oracle breakdown: {verification['INDEPENDENTLY_VERIFIED']} independently verified, {verification['POLICY_DERIVED']} policy-derived, and {unsupported_adjudication} adjudicated. Status remains `NOT_AUTHORITATIVE_BUSINESS_ORACLE / DOMAIN_VALIDATION_PENDING`.

## Reproducibility status

Local source/test/evidence regeneration is available. Clean-environment status is `{reproduction['status']}` because {', '.join(reproduction['missing_dependencies']) or 'the clean runner was not completed'}.

## Next-stage gate

Do not begin temporal replay until the provided clean Docker/CI command completes successfully and its logs/digests are added. Temporal replay status is `NOT_STARTED`.

## Readiness

Decision D - not ready because clean-environment reproduction was not executed successfully.
""")
    return final_data


if __name__ == "__main__":
    print(json.dumps(generate()))
