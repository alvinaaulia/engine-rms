"""Validate schemas and cross-artifact invariants before reports are produced."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent
SCHEMAS = ROOT / "artifact_schemas"
HARDENED_SCHEMAS = ROOT / "artifact-schemas"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(schema_name: str, artifact: Path, schema_root: Path = SCHEMAS) -> None:
    schema = load(schema_root / schema_name)
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(load(artifact)), key=lambda error: list(error.path))
    if errors:
        rendered = "; ".join(f"{'.'.join(map(str, error.path))}: {error.message}" for error in errors[:10])
        raise RuntimeError(f"schema validation failed for {artifact}: {rendered}")


def unique_case_ids(payload: dict, label: str) -> None:
    key = "cases" if "cases" in payload else "results"
    identifiers = [item["case_id"] for item in payload[key]]
    if len(identifiers) != len(set(identifiers)):
        raise RuntimeError(f"duplicate case ID in {label}")


def expected_result_hash(result: dict) -> str:
    payload = {key: value for key, value in result.items() if key != "expected_hash"}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_metric_invariants(payload: dict) -> None:
    for item in payload["metrics"]:
        status = item["status"]
        if status == "MEASURED" and (item.get("value") is None or item.get("denominator") is None):
            raise RuntimeError(f"measured metric lacks value/denominator: {item['metric']}")
        if status != "MEASURED" and (item.get("value") is not None or item.get("denominator") is not None):
            raise RuntimeError(f"unmeasured metric carries numeric value: {item['metric']}")


def validate_verification_invariants(result: dict) -> None:
    if result["expected_hash"] != expected_result_hash(result):
        raise RuntimeError(f"per-case expected hash mismatch: {result['case_id']}")
    if result["verification_status"] == "INDEPENDENTLY_VERIFIED" and (not result.get("verifier_id") or not result.get("verification_timestamp")):
        raise RuntimeError(f"independently verified case lacks verifier evidence: {result['case_id']}")
    if result["verification_status"] == "ADJUDICATED":
        required = ("adjudication_reference", "adjudicator", "decision_date", "written_rationale")
        if any(not result.get(key) for key in required):
            raise RuntimeError(f"unsupported adjudicated case: {result['case_id']}")


def validate_e2e_invariants(payload: dict) -> None:
    identifiers = [item["case_id"] for item in payload["traces"]]
    if payload["case_count"] != len(identifiers) or len(identifiers) != len(set(identifiers)):
        raise RuntimeError("E2E trace count or case IDs are inconsistent")
    for trace in payload["traces"]:
        if trace["result"] == "PASS" and trace["expected_hash"] != trace["actual_hash"]:
            raise RuntimeError(f"E2E PASS has different hashes: {trace['case_id']}")
        if trace["evaluation_category"] == "FULL_PAYROLL_PIPELINE":
            required_steps = {"testing_database", "buildFactsFromDatabase", "PayrollRuleEngineService::execute", "Laravel HTTP client", "Go /execute", "TPR-IR validation", "GRL translation", "GRULE", "Laravel normalization", "salary persistence", "database assertion"}
            required_fields = ("employee_fixture_id", "rate_version_ids", "tax_version_ids", "laravel_service_method", "salary_record_id", "go_internal_path", "go_internal_trace_status")
            if (not required_steps.issubset(set(trace["execution_path"])) or not trace["persistence_asserted"]
                    or any(field not in trace for field in required_fields)):
                raise RuntimeError(f"full-pipeline trace is incomplete: {trace['case_id']}")
        if trace["evaluation_category"] == "LARAVEL_CONFIGURATION_GUARD":
            if (trace.get("go_request_correlation_status") != "NOT_APPLICABLE_REJECTED_BEFORE_HTTP"
                    or trace.get("persistence_asserted") or trace.get("salary_record_id") is not None
                    or not trace.get("database_unchanged")
                    or trace.get("expected_error_codes") != trace.get("actual_error_codes")):
                raise RuntimeError(f"configuration guard evidence is incomplete: {trace['case_id']}")


def validate_report_counts(payload: dict, root: Path = ROOT) -> None:
    """Reject a report data model whose evaluated counts differ from raw artifacts."""
    expected = load(root / "oracle_expected_results.json")
    baseline_actual = load(root / "runs/reconstructed-baseline/actual-results.json")
    baseline_mismatch = load(root / "runs/reconstructed-baseline/mismatch-details.json")
    fixed_actual = load(root / "runs/fixed/actual_results.json")
    fixed_mismatch = load(root / "runs/fixed/mismatch_details.json")
    fixtures = load(root / "translation_validation_fixtures.json")
    traces = load(root / "e2e-execution-traces.json")
    categories = Counter(item["evaluation_category"] for item in traces["traces"])
    verification = Counter(item["verification_status"] for item in expected["results"])
    layers = {item["layer"]: item for item in payload["evaluation_layers"]}
    comparisons = {
        "reconstructed cases": (layers["Reconstructed baseline differential"]["cases"], len(baseline_actual["results"])),
        "reconstructed mismatches": (layers["Reconstructed baseline differential"]["mismatch"], baseline_mismatch["mismatch_count"]),
        "fixed cases": (layers["Fixed differential"]["cases"], len(fixed_actual["results"])),
        "fixed mismatches": (layers["Fixed differential"]["mismatch"], fixed_mismatch["mismatch_count"]),
        "translator fixtures": (layers["Translator fixtures"]["cases"], fixtures["fixture_count"]),
        "full pipeline": (payload["e2e"]["full_pipeline_cases"], categories["FULL_PAYROLL_PIPELINE"]),
        "configuration guards": (payload["e2e"]["configuration_guard_cases"], categories["LARAVEL_CONFIGURATION_GUARD"]),
        "persistence": (payload["e2e"]["persistence_cases"], sum(bool(item["persistence_asserted"]) for item in traces["traces"])),
        "oracle total": (payload["oracle"]["total"], expected["case_count"]),
        "independently verified": (payload["oracle"]["independently_verified"], verification["INDEPENDENTLY_VERIFIED"]),
        "policy derived": (payload["oracle"]["policy_derived"], verification["POLICY_DERIVED"]),
        "unsupported adjudication": (payload["oracle"]["unsupported_adjudication"], verification["ADJUDICATED"]),
    }
    inconsistent = [f"{name}: report={reported}, artifact={actual}" for name, (reported, actual) in comparisons.items() if reported != actual]
    if inconsistent:
        raise RuntimeError("report count mismatch: " + "; ".join(inconsistent))


def main() -> None:
    artifacts = [
        ("cases.schema.json", ROOT / "oracle_input_cases.json"),
        ("expected.schema.json", ROOT / "oracle_expected_results.json"),
    ]
    for run in ("baseline", "fixed"):
        run_dir = ROOT / "runs" / run
        artifacts += [
            ("actual.schema.json", run_dir / "actual_results.json"),
            ("mismatch.schema.json", run_dir / "mismatch_details.json"),
            ("metrics.schema.json", run_dir / "metrics.json"),
            ("manifest.schema.json", run_dir / "manifest.json"),
        ]
    for schema_name, artifact in artifacts:
        if not artifact.exists():
            raise RuntimeError(f"missing required artifact: {artifact}")
        validate(schema_name, artifact)

    hardened_artifacts = [
        ("e2e-trace.schema.json", ROOT / "e2e-execution-traces.json"),
        ("reconstructed-baseline.schema.json", ROOT / "runs/reconstructed-baseline/manifest.json"),
    ]
    meta_files = list((ROOT / "runs/hardening/raw-logs").glob("*.meta.json"))
    meta_files += list((ROOT / "runs/reconstructed-baseline").glob("repeat-*/raw-logs/*.meta.json"))
    for artifact in meta_files:
        hardened_artifacts.append(("test-execution.schema.json", artifact))
    for schema_name, artifact in hardened_artifacts:
        if not artifact.exists():
            raise RuntimeError(f"missing required hardened artifact: {artifact}")
        validate(schema_name, artifact, HARDENED_SCHEMAS)

    corpus = load(ROOT / "oracle_input_cases.json")
    expected = load(ROOT / "oracle_expected_results.json")
    unique_case_ids(corpus, "corpus")
    unique_case_ids(expected, "expected results")
    if corpus["case_count"] != len(corpus["cases"]) or expected["case_count"] != len(expected["results"]):
        raise RuntimeError("declared case count is inconsistent")
    if {item["case_id"] for item in corpus["cases"]} != {item["case_id"] for item in expected["results"]}:
        raise RuntimeError("corpus and expected case sets differ")
    for result in expected["results"]:
        validate_verification_invariants(result)
        if result["policy_hash"] != sha(ROOT / "reference_policy.json"):
            raise RuntimeError(f"per-case policy hash mismatch: {result['case_id']}")
    freeze = load(ROOT / ".oracle_frozen.json")
    for filename, expected_hash in freeze["hashes"].items():
        if sha(ROOT / filename) != expected_hash:
            raise RuntimeError(f"frozen hash mismatch: {filename}")
    for run in ("baseline", "fixed"):
        run_dir = ROOT / "runs" / run
        manifest = load(run_dir / "manifest.json")
        paths = {"policy": ROOT / "reference_policy.json", "corpus": ROOT / "oracle_input_cases.json", "expected": ROOT / "oracle_expected_results.json", "actual": run_dir / "actual_results.json", "mismatches": run_dir / "mismatch_details.json", "metrics": run_dir / "metrics.json"}
        for name, path in paths.items():
            if sha(path) != manifest["hashes"][name]:
                raise RuntimeError(f"manifest hash mismatch: {run}/{name}")
        validate_metric_invariants(load(run_dir / "metrics.json"))
    metric_results = load(ROOT / "metric-results.json")
    Draft202012Validator(load(SCHEMAS / "metrics.schema.json"), format_checker=FormatChecker()).validate(metric_results)
    validate_metric_invariants(metric_results)
    e2e_payload = load(ROOT / "e2e-execution-traces.json")
    validate_e2e_invariants(e2e_payload)
    final_report_data = ROOT / "final-report-data.json"
    if final_report_data.exists():
        validate_report_counts(load(final_report_data))
    report = f"# Artifact schema validation report\n\n{len(artifacts) + len(hardened_artifacts) + 1} artifacts passed JSON Schema and cross-artifact checks. Checks include duplicate IDs, frozen and per-case hashes, run-manifest hashes, metric denominator/nullability, baseline reconstruction provenance, command exit evidence, E2E service traces, and adjudication references.\n"
    (ROOT / "ARTIFACT_SCHEMA_VALIDATION_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"validated_artifacts": len(artifacts) + len(hardened_artifacts) + 1, "status": "PASS"}))


if __name__ == "__main__":
    main()
