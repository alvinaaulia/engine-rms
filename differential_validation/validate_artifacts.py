"""Validate schemas and cross-artifact invariants before reports are produced."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent
SCHEMAS = ROOT / "artifact_schemas"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(schema_name: str, artifact: Path) -> None:
    schema = load(SCHEMAS / schema_name)
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(load(artifact)), key=lambda error: list(error.path))
    if errors:
        rendered = "; ".join(f"{'.'.join(map(str, error.path))}: {error.message}" for error in errors[:10])
        raise RuntimeError(f"schema validation failed for {artifact}: {rendered}")


def unique_case_ids(payload: dict, label: str) -> None:
    key = "cases" if "cases" in payload else "results"
    identifiers = [item["case_id"] for item in payload[key]]
    if len(identifiers) != len(set(identifiers)):
        raise RuntimeError(f"duplicate case ID in {label}")


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

    corpus = load(ROOT / "oracle_input_cases.json")
    expected = load(ROOT / "oracle_expected_results.json")
    unique_case_ids(corpus, "corpus")
    unique_case_ids(expected, "expected results")
    if corpus["case_count"] != len(corpus["cases"]) or expected["case_count"] != len(expected["results"]):
        raise RuntimeError("declared case count is inconsistent")
    if {item["case_id"] for item in corpus["cases"]} != {item["case_id"] for item in expected["results"]}:
        raise RuntimeError("corpus and expected case sets differ")
    for result in expected["results"]:
        if result["verification_status"] == "ADJUDICATED" and not result["adjudication_reference"]:
            raise RuntimeError(f"adjudicated case lacks reference: {result['case_id']}")
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
    report = "# Artifact schema validation report\n\nAll required v2 artifacts passed JSON Schema and cross-artifact checks. Checks include duplicate IDs, frozen hashes, run-manifest hashes, metric nullability, baseline presence, and adjudication references.\n"
    (ROOT / "ARTIFACT_SCHEMA_VALIDATION_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"validated_artifacts": len(artifacts), "status": "PASS"}))


if __name__ == "__main__":
    main()
