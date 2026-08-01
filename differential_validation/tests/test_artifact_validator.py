from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from differential_validation.validate_artifacts import (
    HARDENED_SCHEMAS,
    expected_result_hash,
    load,
    unique_case_ids,
    validate_e2e_invariants,
    validate_metric_invariants,
    validate_report_counts,
    validate_verification_invariants,
)


class ArtifactValidatorTest(unittest.TestCase):
    def test_dockerfile_go_name_does_not_poison_go_module(self) -> None:
        engine = Path(__file__).resolve().parents[2]
        self.assertEqual([], [path for path in engine.rglob("Dockerfile.go") if ".tmp" not in path.parts])

    def test_malformed_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{not-json", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                load(path)

    def test_duplicate_case_id_is_rejected(self) -> None:
        with self.assertRaises(RuntimeError):
            unique_case_ids({"cases": [{"case_id": "PAY-001-01"}, {"case_id": "PAY-001-01"}]}, "test")

    def test_expected_hash_mismatch_is_rejected(self) -> None:
        result = {
            "case_id": "PAY-001-01", "verification_status": "POLICY_DERIVED", "verification_method": "policy",
            "verifier_id": None, "verification_timestamp": None, "adjudication_reference": None,
            "expected_hash": "0" * 64, "policy_hash": "1" * 64, "notes": "test",
        }
        self.assertNotEqual(result["expected_hash"], expected_result_hash(result))
        with self.assertRaises(RuntimeError):
            validate_verification_invariants(result)

    def test_measured_metric_with_null_is_rejected(self) -> None:
        with self.assertRaises(RuntimeError):
            validate_metric_invariants({"metrics": [{"metric": "x", "status": "MEASURED", "value": None, "denominator": 1}]})

    def test_unobservable_metric_with_zero_is_rejected(self) -> None:
        with self.assertRaises(RuntimeError):
            validate_metric_invariants({"metrics": [{"metric": "x", "status": "NOT_OBSERVABLE", "value": 0, "denominator": None}]})

    def test_unsupported_adjudicated_status_is_rejected(self) -> None:
        result = {
            "case_id": "PAY-001-01", "verification_status": "ADJUDICATED", "verification_method": "unknown",
            "verifier_id": None, "verification_timestamp": None, "adjudication_reference": None,
            "expected_hash": "", "policy_hash": "1" * 64, "notes": "",
        }
        result["expected_hash"] = expected_result_hash(result)
        with self.assertRaises(RuntimeError):
            validate_verification_invariants(result)

    def test_reconstructed_baseline_cannot_claim_original(self) -> None:
        schema = load(HARDENED_SCHEMAS / "reconstructed-baseline.schema.json")
        payload = {"baseline_type": "ORIGINAL"}
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(payload)))

    def test_full_pipeline_trace_without_service_path_is_rejected(self) -> None:
        payload = {"case_count": 1, "traces": [{
            "case_id": "E2E-001", "evaluation_category": "FULL_PAYROLL_PIPELINE",
            "execution_path": ["testing_database"], "persistence_asserted": False,
            "result": "PASS", "expected_hash": "a" * 64, "actual_hash": "a" * 64,
        }]}
        with self.assertRaises(RuntimeError):
            validate_e2e_invariants(payload)

    def test_configuration_guard_with_database_change_is_rejected(self) -> None:
        payload = {"case_count": 1, "traces": [{
            "case_id": "E2E-033", "evaluation_category": "LARAVEL_CONFIGURATION_GUARD",
            "execution_path": ["testing_database", "PayrollRuleEngineService::execute", "configuration validation"],
            "persistence_asserted": False, "salary_record_id": None,
            "go_request_correlation_status": "NOT_APPLICABLE_REJECTED_BEFORE_HTTP",
            "database_unchanged": False, "expected_error_codes": ["rules"], "actual_error_codes": ["rules"],
            "result": "PASS", "expected_hash": "a" * 64, "actual_hash": "a" * 64,
        }]}
        with self.assertRaises(RuntimeError):
            validate_e2e_invariants(payload)

    def test_report_count_inconsistent_with_artifact_is_rejected(self) -> None:
        root = Path(__file__).resolve().parents[1]
        report = load(root / "final-report-data.json")
        report["oracle"]["total"] += 1
        with self.assertRaises(RuntimeError):
            validate_report_counts(report, root)


if __name__ == "__main__":
    unittest.main()
