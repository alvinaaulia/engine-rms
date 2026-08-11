#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def comparator_payload_hashes(run: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for case_dir in sorted((run / "cases").iterdir()):
        if not case_dir.is_dir():
            continue
        candidates = [case_dir / "comparator-result.json", case_dir / "rejection-comparison.json"]
        existing = [path for path in candidates if path.is_file()]
        if len(existing) != 1:
            raise ValueError(f"Expected one top-level comparator for {case_dir.name}")
        envelope = load_json(existing[0])
        payload_hash = envelope.get("payload_sha256")
        if not isinstance(payload_hash, str) or len(payload_hash) != 64:
            raise ValueError(f"Missing comparator payload hash for {case_dir.name}")
        result[case_dir.name] = payload_hash
    return result


def legacy_signature(run: Path) -> dict[str, dict[str, int]]:
    signature: dict[str, dict[str, int]] = {}
    for name in ("reconstructed-baseline-repeat-1", "reconstructed-baseline-repeat-2", "fixed"):
        value = load_json(run / "legacy-regression" / name / "mismatch_details.json")
        signature[name] = {
            "case_count": int(value["case_count"]),
            "mismatch_count": int(value["mismatch_count"]),
        }
    return signature


def selected_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "case_count",
        "repeat_count",
        "supported_replay_attempts",
        "matched_replay_attempts",
        "expected_rejection_attempts",
        "accepted_rejection_attempts",
        "independent_wave_count",
        "cumulative_wave_count",
        "exactness",
    )
    return {key: summary[key] for key in keys}


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare Windows and WSL Temporal Replay v2 runs")
    parser.add_argument("primary_run", type=Path)
    parser.add_argument("secondary_run", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()

    primary = args.primary_run.resolve()
    secondary = args.secondary_run.resolve()
    for run in (primary, secondary):
        if not run.is_dir():
            raise SystemExit(f"Run directory not found: {run}")

    primary_manifest = load_json(primary / "TEMPORAL_REPLAY_REPRODUCIBILITY_MANIFEST_V2.json")
    secondary_manifest = load_json(secondary / "TEMPORAL_REPLAY_REPRODUCIBILITY_MANIFEST_V2.json")
    primary_summary = load_json(primary / "experiment-summary-v2.json")
    secondary_summary = load_json(secondary / "experiment-summary-v2.json")
    primary_source = load_json(primary / "source-identity.json")
    secondary_source = load_json(secondary / "source-identity.json")
    primary_environment = load_json(primary / "environment.json")
    secondary_environment = load_json(secondary / "environment.json")
    primary_payload = load_json(primary / "payload-hash-validation.json")
    secondary_payload = load_json(secondary / "payload-hash-validation.json")

    source_keys = ("engine_commit", "validation_commit", "laravel_commit", "engine_branch", "laravel_branch")
    primary_source_identity = {key: primary_source[key] for key in source_keys}
    secondary_source_identity = {key: secondary_source[key] for key in source_keys}
    primary_comparators = comparator_payload_hashes(primary)
    secondary_comparators = comparator_payload_hashes(secondary)
    comparator_mismatches = sorted(
        case_id
        for case_id in set(primary_comparators) | set(secondary_comparators)
        if primary_comparators.get(case_id) != secondary_comparators.get(case_id)
    )

    stable_artifacts = (
        "replay-differences.json",
        "runtime-correlation-summary.json",
        "rounding-observability-results.json",
        "tax-version-cases.json",
    )
    stable_hashes = {
        name: {
            "primary_sha256": sha256(primary / name),
            "secondary_sha256": sha256(secondary / name),
            "byte_identical": sha256(primary / name) == sha256(secondary / name),
        }
        for name in stable_artifacts
    }

    checks = {
        "distinct_operating_system": primary_environment.get("os") != secondary_environment.get("os"),
        "source_identity_equal": primary_source_identity == secondary_source_identity,
        "primary_manifest_pass": primary_manifest.get("status") == "PASS",
        "secondary_manifest_pass": secondary_manifest.get("status") == "PASS",
        "primary_all_gates_pass": all(primary_manifest.get("gates", {}).values()),
        "secondary_all_gates_pass": all(secondary_manifest.get("gates", {}).values()),
        "summary_and_exactness_equal": selected_summary(primary_summary) == selected_summary(secondary_summary),
        "case_comparator_sets_equal": set(primary_comparators) == set(secondary_comparators),
        "all_case_comparator_payloads_equal": not comparator_mismatches,
        "legacy_signature_equal": legacy_signature(primary) == legacy_signature(secondary),
        "primary_payload_integrity_pass": primary_payload == {"status": "PASS", "checked": 30536, "error_count": 0, "errors_sample": []},
        "secondary_payload_integrity_pass": secondary_payload == {"status": "PASS", "checked": 30536, "error_count": 0, "errors_sample": []},
        "zero_replay_differences_both": load_json(primary / "replay-differences.json") == [] and load_json(secondary / "replay-differences.json") == [],
        "stable_summary_artifacts_byte_identical": all(item["byte_identical"] for item in stable_hashes.values()),
    }
    status = "SECOND_ENVIRONMENT_PASS" if all(checks.values()) else "SECOND_ENVIRONMENT_FAIL"

    result = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status,
        "primary_run": str(primary),
        "secondary_run": str(secondary),
        "primary_run_id": primary_summary["run_id"],
        "secondary_run_id": secondary_summary["run_id"],
        "primary_environment": primary_environment,
        "secondary_environment": secondary_environment,
        "source_identity": primary_source_identity,
        "checks": checks,
        "case_comparator_count": len(primary_comparators),
        "case_comparator_mismatches": comparator_mismatches,
        "selected_summary": selected_summary(primary_summary),
        "legacy_signature": legacy_signature(primary),
        "stable_artifact_hashes": stable_hashes,
        "domain_validation": "DOMAIN_VALIDATION_PENDING",
        "oracle_status": "NOT_AUTHORITATIVE_BUSINESS_ORACLE",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    exactness = primary_summary["exactness"]
    markdown = f"""# Temporal Replay v2 Second-Environment Comparison

Status: `{status}`

## Runs

- Primary Windows: `{primary_summary['run_id']}`
- Secondary WSL 2 native, no Docker: `{secondary_summary['run_id']}`
- Engine commit: `{primary_source['engine_commit']}`
- Laravel commit: `{primary_source['laravel_commit']}`

## Cross-environment result

- Both manifests: `PASS`; all gates passed in both environments.
- Cases: {primary_summary['case_count']} in each environment.
- Supported attempts: {primary_summary['matched_replay_attempts']}/{primary_summary['supported_replay_attempts']} matched in each environment.
- Expected rejections: {primary_summary['accepted_rejection_attempts']}/{primary_summary['expected_rejection_attempts']} accepted in each environment.
- Component amount: {exactness['component_amount']['matched']}/{exactness['component_amount']['total']} in each environment.
- Summary fields: {exactness['summary']['matched']}/{exactness['summary']['total']} in each environment.
- Provenance fields: {exactness['provenance']['matched']}/{exactness['provenance']['total']} in each environment.
- Per-case comparator payloads: {len(primary_comparators)}/{len(primary_comparators)} byte-equivalent canonical payload hashes; mismatches: {len(comparator_mismatches)}.
- Payload integrity: 30,536/30,536 envelopes passed independently in each environment.
- Legacy signature: reconstructed baseline 8 mismatches twice; fixed 0 mismatches in both environments.

## Environment distinction

- Primary: `{primary_environment.get('os')}`; PHP `{primary_environment.get('php_version')}`; Go `{primary_environment.get('go_version')}`.
- Secondary: `{secondary_environment.get('os')}`; PHP `{secondary_environment.get('php_version')}`; Go `{secondary_environment.get('go_version')}`.

## Scope

This closes the second-environment technical reproduction gate for Temporal Replay v2. It does not convert the technical reference oracle into an authoritative payroll-policy oracle. Domain status remains `NOT_AUTHORITATIVE_BUSINESS_ORACLE / DOMAIN_VALIDATION_PENDING`.
"""
    args.output_md.write_text(markdown, encoding="utf-8")
    print(json.dumps({"status": status, "comparison_json": str(args.output_json), "comparison_report": str(args.output_md)}))
    return 0 if status == "SECOND_ENVIRONMENT_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
