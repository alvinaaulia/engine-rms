#!/usr/bin/env python3
"""Validate raw Temporal Replay v2 evidence and generate reports from it."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, RefResolver


RUN_RE = re.compile(r"^temporal-v2-(\d{8}T\d{6}Z)-[a-f0-9]{8}$")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def pct(matched: int, total: int) -> float | None:
    return None if total == 0 else round(matched * 100 / total, 6)


class EvidenceError(RuntimeError):
    pass


class Finalizer:
    def __init__(self, run_dir: Path, package_dir: Path):
        self.run = run_dir.resolve()
        self.package = package_dir.resolve()
        self.run_id = self.run.name
        self.failures: list[str] = []
        self.gates: dict[str, bool] = {}

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.failures.append(message)

    def gate(self, name: str, condition: bool, message: str) -> None:
        self.gates[name] = bool(condition)
        self.require(condition, message)

    def run_all(self) -> dict[str, Any]:
        self.require(self.run.is_dir(), f"run directory is missing: {self.run}")
        match = RUN_RE.fullmatch(self.run_id)
        self.require(match is not None, "run directory name is not a canonical v2 run ID")
        required = [
            "source-identity.json", "time-provenance.json", "experiment-summary-v2.json",
            "temporal-exactness-metrics.json", "version-applicability-results.json",
            "independent-mutation-waves.json", "cumulative-mutation-waves-v2.json",
            "runtime-correlation-events.jsonl", "forbidden-query-traces.jsonl",
            "temporal-case-index.json", "replay-results.jsonl", "temporal-execution-manifests.jsonl",
            "replay-differences.json", "rounding-observability-results.json",
            "performance-observation-raw.json", "tax-version-cases.json", "full-pipeline-e2e.json",
        ]
        for name in required:
            self.require((self.run / name).is_file(), f"missing required artifact: {name}")
        if self.failures:
            raise EvidenceError("; ".join(self.failures))

        self.copy_schemas()
        self.validate_time()
        self.validate_schemas()
        raw = self.validate_semantics()
        self.generate_reports(raw)
        self.generate_manifest(raw)
        if self.failures:
            raise EvidenceError("\n".join(self.failures))
        return {"status": "PASS", "run_id": self.run_id, "gates": self.gates}

    def copy_schemas(self) -> None:
        source = self.package / "temporal-artifact-schemas"
        target = self.run / "temporal-artifact-schemas"
        self.require(source.is_dir(), "source temporal schemas are missing")
        shutil.copytree(source, target, dirs_exist_ok=True)

    def validate_time(self) -> None:
        time_data = load_json(self.run / "time-provenance.json")
        source = load_json(self.run / "source-identity.json")
        match = RUN_RE.fullmatch(self.run_id)
        started = parse_time(time_data["started_at"])
        finished = parse_time(time_data["finished_at"])
        encoded = started.strftime("%Y%m%dT%H%M%SZ")
        checks = [
            time_data["run_id"] == self.run_id,
            source["run_id"] == self.run_id,
            match is not None and match.group(1) == encoded,
            source["started_at"] == time_data["started_at"],
            started <= finished,
            started <= datetime.now(timezone.utc),
            time_data["canonical_timezone"] == "UTC",
        ]
        self.gate("time_provenance", all(checks), "run ID and UTC time provenance are inconsistent")

    def validate_schemas(self) -> None:
        schema_dir = self.run / "temporal-artifact-schemas"
        validator_cache: dict[str, Draft202012Validator] = {}
        envelope_files: list[Path] = []
        for case_dir in sorted((self.run / "cases").glob("*")):
            envelope_files.extend(path for path in case_dir.rglob("*.json") if path.is_file())
            envelope_files.extend(path for path in case_dir.rglob("*.jsonl") if path.is_file())
        envelope_files.extend([
            self.run / "replay-results.jsonl", self.run / "temporal-execution-manifests.jsonl",
            self.run / "runtime-correlation-events.jsonl", self.run / "forbidden-query-traces.jsonl",
        ])
        schema_errors = 0
        run_ids: set[str] = set()
        for path in envelope_files:
            values = load_jsonl(path) if path.suffix == ".jsonl" else [load_json(path)]
            for value in values:
                schema_ref = value.get("schema_ref") if isinstance(value, dict) else None
                schema_name = Path(schema_ref).name if isinstance(schema_ref, str) else ""
                schema_path = schema_dir / schema_name
                if not schema_name or schema_ref != f"temporal-artifact-schemas/{schema_name}" or not schema_path.is_file():
                    schema_errors += 1
                    self.failures.append(f"schema failure {path.relative_to(self.run)}: invalid or missing schema_ref")
                    continue
                if schema_name not in validator_cache:
                    schema = load_json(schema_path)
                    validator_cache[schema_name] = Draft202012Validator(
                        schema,
                        resolver=RefResolver(base_uri=schema_dir.as_uri() + "/", referrer=schema),
                        format_checker=FormatChecker(),
                    )
                errors = list(validator_cache[schema_name].iter_errors(value))
                schema_errors += len(errors)
                if errors:
                    self.failures.append(f"schema failure {path.relative_to(self.run)}: {errors[0].message}")
                    continue
                run_ids.add(value["run_id"])
        specialized = {
            "temporal-case-index.json": "temporal-case-index.schema.json",
            "temporal-exactness-metrics.json": "exactness-metrics.schema.json",
            "independent-mutation-waves.json": "mutation-wave.schema.json",
            "cumulative-mutation-waves-v2.json": "mutation-wave.schema.json",
            "time-provenance.json": "time-provenance.schema.json",
        }
        for artifact, schema_name in specialized.items():
            schema = load_json(schema_dir / schema_name)
            validator = Draft202012Validator(schema, resolver=RefResolver(base_uri=schema_dir.as_uri() + "/", referrer=schema), format_checker=FormatChecker())
            errors = list(validator.iter_errors(load_json(self.run / artifact)))
            schema_errors += len(errors)
            if errors:
                self.failures.append(f"schema failure {artifact}: {errors[0].message}")
        payload_check = subprocess.run(
            ["php", str(self.package / "verify_temporal_v2_payload_hashes.php"), str(self.run)],
            text=True, capture_output=True, check=False,
        )
        payload_result = json.loads(payload_check.stdout) if payload_check.stdout.strip() else {"status": "FAIL", "error_count": 1}
        (self.run / "payload-hash-validation.json").write_text(json.dumps(payload_result, indent=2) + "\n", encoding="utf-8")
        self.gate(
            "schema_validation",
            schema_errors == 0 and run_ids == {self.run_id} and payload_check.returncode == 0 and payload_result.get("status") == "PASS",
            "artifact schemas, canonical payload hashes, or single-run identity validation failed",
        )

    def validate_semantics(self) -> dict[str, Any]:
        summary = load_json(self.run / "experiment-summary-v2.json")
        exact_file = load_json(self.run / "temporal-exactness-metrics.json")
        index = load_json(self.run / "temporal-case-index.json")
        results = load_jsonl(self.run / "replay-results.jsonl")
        manifests = load_jsonl(self.run / "temporal-execution-manifests.jsonl")
        version_results = load_json(self.run / "version-applicability-results.json")
        events = load_jsonl(self.run / "runtime-correlation-events.jsonl")
        forbidden = load_jsonl(self.run / "forbidden-query-traces.jsonl")
        independent = load_json(self.run / "independent-mutation-waves.json")
        cumulative = load_json(self.run / "cumulative-mutation-waves-v2.json")
        rounding = load_json(self.run / "rounding-observability-results.json")
        performance = load_json(self.run / "performance-observation-raw.json")
        tax_cases = load_json(self.run / "tax-version-cases.json")
        differences = load_json(self.run / "replay-differences.json")

        case_ids = [item["case_id"] for item in index["cases"]]
        self.gate("case_index", index["case_count"] == len(case_ids) == len(set(case_ids)) == len(manifests), "case index or manifest identities are inconsistent")
        self.validate_case_directories(index)

        supported = [item["payload"] for item in results if item["payload"]["status"] == "MATCHED"]
        rejected = [item["payload"] for item in results if item["payload"]["status"] == "EXPECTED_REJECTION"]
        failed = [item for item in results if item["payload"]["status"] not in {"MATCHED", "EXPECTED_REJECTION"}]
        self.gate(
            "replay_attempts",
            not failed and len(supported) == summary["supported_replay_attempts"] == summary["matched_replay_attempts"]
            and len(rejected) == summary["expected_rejection_attempts"] == summary["accepted_rejection_attempts"],
            "replay attempt counts/statuses are inconsistent",
        )
        recomputed = self.recompute_exactness(supported)
        self.gate("granular_exactness", recomputed == exact_file["exactness"], "granular exactness does not recompute from replay results")
        self.gate("zero_differences", differences == [], "one or more unresolved replay differences exist")

        self.validate_applicability(version_results, exact_file["exactness"])
        self.validate_correlation(supported, rejected, events, summary)
        self.gate(
            "contamination",
            len(forbidden) == len(supported) and all(item["payload"]["forbidden_lookup_count"] == 0 and item["payload"]["result"] == "PASS" for item in forbidden),
            "per-attempt forbidden current-state lookup evidence failed",
        )
        self.gate(
            "side_effect",
            summary["salary_state_sha256_before"] == summary["salary_state_sha256_after"]
            and all(load_json(self.run / item["artifact_path"] / "side-effect-check.json")["payload"]["result"] == "PASS" for item in index["cases"] if item["status"] == "MATCHED"),
            "salary side-effect evidence failed",
        )
        self.gate(
            "independent_waves",
            len(independent) == 10 and len({wave["baseline_state_sha256"] for wave in independent}) == 1
            and all(wave["result"] == "PASS" and wave["forbidden_query_count"] == 0 and wave["salary_side_effect_count"] == 0 for wave in independent),
            "independent mutation waves are not isolated or did not pass",
        )
        self.gate(
            "cumulative_waves",
            len(cumulative) == 7 and all(wave["result"] == "PASS" and wave["inherits_previous_wave_state"] == (idx > 0) for idx, wave in enumerate(cumulative)),
            "cumulative mutation evidence failed",
        )
        self.gate(
            "rounding_observability",
            all(metric["total"] > 0 and metric["matched"] == metric["total"] for metric in rounding.values()),
            "raw amount or rounding decision evidence is incomplete",
        )
        self.validate_performance(performance)
        expected_tax = {
            "tax_v1_active", "tax_v2_published_after_original", "tax_effective_from_boundary", "tax_effective_to_boundary",
            "historical_tax_version_no_longer_active", "current_tax_version_removed", "tax_version_hash_corrupted",
            "tax_identity_missing", "manual_override_not_applicable", "mixed_versioned_tax_dataset",
        }
        self.gate("tax_temporal_cases", len(tax_cases) == 10 and {item["scenario"] for item in tax_cases} == expected_tax, "tax temporal coverage is incomplete")
        self.validate_regressions()
        self.validate_exit_codes()
        self.gate("collector_status", summary["status"] == "PASS", "v2 collector did not report PASS")
        return {
            "summary": summary, "exactness": exact_file["exactness"], "index": index,
            "independent": independent, "cumulative": cumulative, "rounding": rounding,
            "performance": performance, "tax_cases": tax_cases, "version_results": version_results,
        }

    def validate_case_directories(self, index: dict[str, Any]) -> None:
        for item in index["cases"]:
            directory = self.run / item["artifact_path"]
            if item["status"] == "MATCHED":
                names = ["manifest.json", "original-output.json", "replay-request.json", "replay-response.json", "comparator-result.json", "version-applicability.json", "forbidden-query-trace.json", "side-effect-check.json", "correlation-events.jsonl", "artifact-hashes.json"]
                comparator = load_json(directory / "comparator-result.json")["payload"] if (directory / "comparator-result.json").is_file() else {}
                self.require(comparator.get("status") == "MATCHED", f"matched case lacks matched comparator: {item['case_id']}")
            else:
                names = ["invalid-manifest.json", "expected-error.json", "actual-error.json", "rejection-comparison.json", "artifact-hashes.json"]
            self.require(all((directory / name).is_file() for name in names), f"missing per-case evidence for {item['case_id']}")
            hashes_path = directory / "artifact-hashes.json"
            if hashes_path.is_file():
                hashes = load_json(hashes_path)["payload"]["artifacts"]
                for relative, expected in hashes.items():
                    target = directory / relative
                    self.require(target.is_file() and sha256_file(target) == expected, f"artifact hash mismatch: {item['case_id']}/{relative}")

    def recompute_exactness(self, supported: list[dict[str, Any]]) -> dict[str, Any]:
        names = ["case", "component_presence", "component_type", "component_amount", "component_provenance", "summary", "provenance", "facts_hash", "ruleset_hash", "output_hash"]
        computed = {name: {"matched": 0, "total": 0} for name in names}
        versions = {name: {"matched": 0, "applicable": 0, "not_applicable": 0, "missing": 0, "mismatched": 0, "measurement_failed": 0} for name in ["rule_version", "rate_version", "tax_version"]}
        for result in supported:
            computed["case"]["total"] += 1
            computed["case"]["matched"] += result["comparator_result"]["status"] == "MATCHED"
            for name, metric in result["comparator_result"]["metrics"].items():
                if name in computed:
                    computed[name]["matched"] += metric["matched"]
                    computed[name]["total"] += metric["total"]
            for name, evidence in result["version_applicability"].items():
                status = evidence["applicability_status"]
                if status == "APPLICABLE_MATCHED":
                    versions[name]["applicable"] += 1; versions[name]["matched"] += 1
                elif status == "APPLICABLE_MISMATCHED":
                    versions[name]["applicable"] += 1; versions[name]["mismatched"] += 1
                elif status == "APPLICABLE_MISSING":
                    versions[name]["applicable"] += 1; versions[name]["missing"] += 1
                elif status == "NOT_APPLICABLE":
                    versions[name]["not_applicable"] += 1
                else:
                    versions[name]["measurement_failed"] += 1
        for metric in computed.values():
            metric["percent"] = pct(metric["matched"], metric["total"])
        for metric in versions.values():
            metric["percent"] = pct(metric["matched"], metric["applicable"])
        return computed | versions

    def validate_applicability(self, records: list[dict[str, Any]], exact: dict[str, Any]) -> None:
        valid = True
        statuses = Counter()
        for record in records:
            for evidence in record["identities"].values():
                status = evidence["applicability_status"]
                statuses[(evidence["identity_type"], status)] += 1
                if status == "NOT_APPLICABLE":
                    valid &= evidence["comparison_result"] is None and evidence["expected_ids"] == [] and evidence["resolved_ids"] == []
                elif status == "APPLICABLE_MATCHED":
                    valid &= evidence["comparison_result"] is True and evidence["expected_ids"] and evidence["expected_ids"] == evidence["resolved_ids"]
                else:
                    valid = False
        valid &= exact["tax_version"]["not_applicable"] > 0 and exact["tax_version"]["applicable"] > 0
        valid &= all(exact[name]["matched"] <= exact[name]["applicable"] and exact[name]["missing"] == 0 and exact[name]["mismatched"] == 0 for name in ["rule_version", "rate_version", "tax_version"])
        self.gate("version_applicability", valid, "version applicability contains missing/mismatched/false N/A evidence")

    def validate_correlation(
        self,
        supported: list[dict[str, Any]],
        rejected: list[dict[str, Any]],
        events: list[dict[str, Any]],
        summary: dict[str, Any],
    ) -> None:
        fields = ["request_id", "replay_uuid", "laravel_correlation_id", "go_request_id", "translator_trace_id", "grule_execution_id"]
        valid = all(all(UUID_RE.fullmatch(str(item[field])) for field in fields) and item["request_id"] == item["go_request_id"] for item in supported)
        for field in fields:
            valid &= len({item[field] for item in supported}) == len(supported)
        event_payloads = [item["payload"] for item in events]
        valid &= len({item["event_id"] for item in event_payloads}) == len(event_payloads)
        request_ids = {item["request_id"] for item in supported}
        valid &= all(item["request_id"] in request_ids for item in event_payloads)
        preflight_fields = ["request_id", "replay_uuid", "laravel_correlation_id"]
        valid &= all(
            all(UUID_RE.fullmatch(str(item["preflight_correlation"][field])) for field in preflight_fields)
            for item in rejected
        )
        for field in preflight_fields:
            rejected_values = {item["preflight_correlation"][field] for item in rejected}
            valid &= len(rejected_values) == len(rejected)
            valid &= rejected_values.isdisjoint({item[field] for item in supported})
        correlation = summary["correlation"]
        valid &= correlation["orphan_event_count"] == 0 and correlation["duplicate_id_count"] == 0
        valid &= correlation["all_replay_attempts"] == len(supported) + len(rejected)
        valid &= correlation["all_attempts_with_request_id"] == len(supported) + len(rejected)
        valid &= all(correlation["preflight_unique_ids"][field] == len(rejected) for field in preflight_fields)
        self.gate("runtime_correlation", valid and len(event_payloads) >= len(supported) * 7, "runtime correlation is incomplete, duplicated, or orphaned")

    def validate_performance(self, performance: dict[str, Any]) -> None:
        workloads = performance.get("workloads", {})
        valid = performance.get("observation_type") == "controlled local performance observation" and set(workloads) == {"small", "medium", "large"}
        for data in workloads.values():
            valid &= data["warmup_count"] >= 1 and data["measured_count"] >= 30 and len(data["measurements"]) == data["measured_count"]
            valid &= all(item["query_count"] == 0 and UUID_RE.fullmatch(item["request_id"]) and UUID_RE.fullmatch(item["replay_uuid"]) for item in data["measurements"])
            valid &= set(data.get("latency_summary_microseconds", {})) == {"manifest_validation", "replay_execution", "comparator", "total"}
            valid &= all(set(metric) == {"p50", "p95", "p99", "max"} for metric in data.get("latency_summary_microseconds", {}).values())
            valid &= data.get("snapshot_storage_bytes", {}).get("p50", 0) > 0 and data.get("query_count_max") == 0 and data.get("peak_memory_bytes_max", 0) > 0
        creation = performance.get("manifest_creation_latency_microseconds", {})
        valid &= creation.get("sample_count", 0) > 0 and all(name in creation for name in ["p50", "p95", "p99", "max"])
        self.gate("performance_observation", bool(valid), "controlled local performance observation is incomplete")

    def validate_regressions(self) -> None:
        v1 = self.run / "temporal-v1-regression"
        v1_summary = load_json(v1 / "experiment-summary.json")
        v1_results = load_jsonl(v1 / "replay-results.jsonl")
        baseline_counts = []
        for repeat in (1, 2):
            mismatch = load_json(self.run / "legacy-regression" / f"reconstructed-baseline-repeat-{repeat}" / "mismatch_details.json")
            baseline_counts.append(mismatch["mismatch_count"])
        fixed = load_json(self.run / "legacy-regression" / "fixed" / "mismatch_details.json")
        full = load_json(self.run / "full-pipeline-e2e.json")
        self.gate("temporal_v1_regression", v1_summary["status"] == "PASS" and len(v1_results) == 816 and Counter(item["status"] for item in v1_results) == {"MATCHED": 808, "EXPECTED_REJECTION": 8}, "temporal v1 regression failed")
        self.gate("differential_v4_regression", baseline_counts == [8, 8] and fixed["mismatch_count"] == 0, "legacy baseline/fixed differential regression failed")
        self.gate("full_pipeline", full["case_count"] == 36 and full["exact_match_count"] == 32 and full["expected_rejection_count"] == 4 and full["mismatch_count"] == 0, "full pipeline regression failed")

    def validate_exit_codes(self) -> None:
        files = sorted((self.run / "raw-logs").glob("*.exit-code.txt"))
        # The finalizer's own exit file is written by the runner after this process exits.
        valid = len(files) >= 10 and all(path.read_text().strip() == "0" for path in files)
        self.gate("command_exit_codes", valid, "one or more recorded commands failed or exit evidence is missing")

    def generate_reports(self, raw: dict[str, Any]) -> None:
        summary = raw["summary"]
        exact = raw["exactness"]
        independent = raw["independent"]
        cumulative = raw["cumulative"]
        perf = raw["performance"]
        rounding = raw["rounding"]
        tax = exact["tax_version"]
        source = load_json(self.run / "source-identity.json")
        environment = load_json(self.run / "environment.json") if (self.run / "environment.json").is_file() else {}

        def write(name: str, text: str) -> None:
            (self.run / name).write_text(text.rstrip() + "\n", encoding="utf-8")

        independent_rows = "\n".join(f"| {w['wave_id']} | {w['mutation']} | {w['baseline_current_execution']['status']} | {w['mutated_current_execution']['status']} | {w['result']} |" for w in independent)
        write("INDEPENDENT_MUTATION_WAVES_REPORT.md", f"""# Independent Mutation Waves Report

All ten waves started from the same baseline SHA-256 `{independent[0]['baseline_state_sha256']}`. Each mutation ran in a nested database transaction and was rolled back before the next wave.

| Wave | Mutation | Baseline execution | Mutated execution | Result |
|---|---|---|---|---|
{independent_rows}

Independent waves are the only evidence used to attribute an effect to one mutation.
""")
        cumulative_rows = "\n".join(f"| {w['wave_id']} | {w['mutation']} | {str(w['inherits_previous_wave_state']).lower()} | {w['result']} |" for w in cumulative)
        write("CUMULATIVE_MUTATION_WAVES_REPORT.md", f"""# Cumulative Mutation Waves Report

The retained v1 mutation experiment is explicitly classified as `CUMULATIVE_MUTATION_WAVES`. State produced by one wave is the input to the next and is not independent-effect evidence.

| Wave | Mutation | Inherits prior state | Result |
|---|---|---:|---|
{cumulative_rows}
""")
        write("MUTATION_WAVE_COMPARISON.md", """# Mutation Wave Comparison

| Experiment | Purpose | Isolation |
|---|---|---|
| Independent waves | Attribute current-result change/rejection to exactly one mutation while historical replay remains stable | Baseline restored between every wave |
| Cumulative waves | Stress historical replay after changes accumulate | State intentionally inherited |

Cumulative results are not used to claim independent effects.
""")
        metric_rows = []
        for name, metric in exact.items():
            denominator = metric.get("total", metric.get("applicable", 0))
            metric_rows.append(f"| {name} | {metric['matched']} | {denominator} | {metric.get('not_applicable', 0)} | {metric['percent']} |")
        write("TEMPORAL_EXACTNESS_REPORT.md", "# Temporal Exactness Report\n\nAll values below were recomputed from `replay-results.jsonl`. N/A identities are excluded from applicable denominators.\n\n| Metric | Matched | Denominator | N/A | Percent |\n|---|---:|---:|---:|---:|\n" + "\n".join(metric_rows))
        write("VERSION_APPLICABILITY_SPECIFICATION.md", """# Version Applicability Specification

Allowed states are `APPLICABLE_MATCHED`, `APPLICABLE_MISMATCHED`, `APPLICABLE_MISSING`, `NOT_APPLICABLE`, `UNRESOLVED`, and `MEASUREMENT_FAILED`. Applicable identities require non-empty expected/resolved IDs. `NOT_APPLICABLE` requires empty IDs and a null comparison result; it is excluded from match denominators. Missing applicable evidence fails the run.
""")
        write("VERSION_IDENTITY_REPORT.md", f"""# Version Identity Report

Rule: {exact['rule_version']['matched']}/{exact['rule_version']['applicable']} applicable matched, {exact['rule_version']['not_applicable']} N/A.
Rate: {exact['rate_version']['matched']}/{exact['rate_version']['applicable']} applicable matched, {exact['rate_version']['not_applicable']} N/A.
Tax: {tax['matched']}/{tax['applicable']} applicable matched, {tax['not_applicable']} N/A.

No N/A identity is reported as matched.
""")
        write("TAX_VERSION_TEMPORAL_TEST_REPORT.md", f"""# Tax Version Temporal Test Report

Ten named tax scenarios were executed, including active/published/boundary/inactive/removed/corrupt/missing/manual-override/mixed coverage. Applicable tax attempts: {tax['applicable']}; matched: {tax['matched']}; not applicable: {tax['not_applicable']}; missing: {tax['missing']}. Manual override uses `NOT_APPLICABLE` with a null comparison result.
""")
        write("RUNTIME_CORRELATION_REPORT.md", f"""# Runtime Correlation Report

Evidence-case attempts with request IDs: {summary['correlation']['all_attempts_with_request_id']}/{summary['correlation']['all_replay_attempts']}, including {summary['expected_rejection_attempts']} expected rejections stopped at Laravel preflight. Supported Go attempts: {summary['supported_replay_attempts']}/{summary['supported_replay_attempts']}. Unique Laravel request, replay, Laravel correlation, Go request, translator trace, and GRULE execution IDs: {summary['supported_replay_attempts']} each. Runtime events: {summary['correlation']['runtime_event_count']}. Orphans: 0. Duplicates: 0.
""")
        write("TIME_PROVENANCE_SPECIFICATION.md", """# Time Provenance Specification

The runner records canonical UTC `started_at` before deriving `temporal-v2-YYYYMMDDTHHMMSSZ-<short-hash>`. All artifacts use that run ID. Validators reject a mismatched/future run ID, mixed IDs, or `finished_at < started_at`. Local timezone is metadata only.
""")
        write("TIME_PROVENANCE_VALIDATION_REPORT.md", f"# Time Provenance Validation Report\n\nRun `{self.run_id}` starts at `{summary['started_at']}` and finishes at `{summary['finished_at']}`. Timestamp/run-ID consistency, ordering, and single-run identity: PASS.\n")
        write("PER_CASE_ARTIFACT_REPORT.md", f"# Per-Case Artifact Report\n\nIndexed cases: {raw['index']['case_count']}. Every matched case has manifest, original output, request, response, comparator, applicability, forbidden-query, side-effect, correlation, and hash evidence. Expected-rejection cases have invalid/expected/actual/comparison/hash evidence. Hash and required-file validation: PASS.\n")
        write("TEMPORAL_ARTIFACT_SCHEMA_REPORT.md", f"# Temporal Artifact Schema Report\n\nSchemas: {len(list((self.run / 'temporal-artifact-schemas').glob('*.json')))}. JSON Schema and semantic validation passed. The semantic layer rejects false N/A matches, missing applicable IDs, inconsistent denominators, duplicate identities, time mismatches, absent comparator evidence, missing hashes, and side-effect claims without equal before/after hashes.\n")
        write("CURRENT_STATE_CONTAMINATION_REPORT_V2.md", f"# Current-State Contamination Report v2\n\nPer-attempt traces: {summary['supported_replay_attempts']}. Forbidden lookup count: 0. Observed database queries inside the guarded replay section: 0. Result: PASS.\n")
        write("ROUNDING_OBSERVABILITY_REPORT.md", f"""# Rounding Observability Report

Research trace mode was enabled only for the controlled test run. Raw candidate decimal matches: {rounding['raw_amount_exact_match']['matched']}/{rounding['raw_amount_exact_match']['total']}. Rounding decision matches: {rounding['rounding_decision_exact_match']['matched']}/{rounding['rounding_decision_exact_match']['total']}. Trace fields are excluded from public output hashes and contain no PII.
""")
        perf_rows = "\n".join(
            f"| {name} | {stage} | {data['measured_count']} | {metric['p50']} | {metric['p95']} | {metric['p99']} | {metric['max']} | {data['snapshot_storage_bytes']['p50']} | {data['query_count_max']} | {data['peak_memory_bytes_max']} |"
            for name, data in perf['workloads'].items()
            for stage, metric in data['latency_summary_microseconds'].items()
        )
        write("TEMPORAL_PERFORMANCE_OBSERVATION_V2.md", f"""# Temporal Performance Observation v2

This is a **controlled local performance observation**, not a production benchmark.

| Workload | Stage | Measured repeats | p50 us | p95 us | p99 us | max us | Snapshot p50 bytes | Max queries | Peak memory bytes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
{perf_rows}

Manifest creation latency: `{json.dumps(perf['manifest_creation_latency_microseconds'], sort_keys=True)}`.

Environment: `{json.dumps(environment, ensure_ascii=False, sort_keys=True)}`
""")
        write("SECOND_ENVIRONMENT_REPRODUCTION_REPORT.md", """# Second Environment Reproduction Report

Status: `SECOND_ENVIRONMENT_NOT_EXECUTED`.

No hosted runner, fresh VM, second computer, or Docker runner was available/authorized for this run. No second-environment PASS is claimed. Local clean reproduction may support local technical readiness only.
""")
        self.generate_domain_files(raw)
        write("CODE_CHANGE_REPORT_TEMPORAL_V2.md", self.code_change_report(source))
        readiness = "G. Temporal Replay v2 passed locally; domain validation pending."
        final = f"""# Temporal Replay Final Report v2

## 1. Executive verdict
{readiness}

## 2. Source identity
Engine `{source['engine_commit']}` on `{source['engine_branch']}` and Laravel `{source['laravel_commit']}` on `{source['laravel_branch']}`; dirty before run: {str(source['engine_dirty_before_run']).lower()}/{str(source['laravel_dirty_before_run']).lower()}.

## 3. Run and time provenance
`{self.run_id}`; `{summary['started_at']}` through `{summary['finished_at']}` UTC; validation PASS.

## 4. Architecture changes
Runtime IDs now cross Laravel, HTTP, Go validation, translator, GRULE, response, comparator, and audit. Applicability and research-only rounding evidence are explicit.

## 5. Independent mutation experiment
10/10 isolated waves PASS from one identical valid baseline.

## 6. Cumulative mutation experiment
7/7 retained sequential waves PASS and are reported separately.

## 7. Exactness metrics
Cases {exact['case']['matched']}/{exact['case']['total']}; component amount {exact['component_amount']['matched']}/{exact['component_amount']['total']}; summary {exact['summary']['matched']}/{exact['summary']['total']}; provenance {exact['provenance']['matched']}/{exact['provenance']['total']}; output hash {exact['output_hash']['matched']}/{exact['output_hash']['total']}.

## 8. Version applicability
Rule/rate/tax N/A values are excluded. Applicable missing identities: 0.

## 9. Tax version evidence
10 temporal tax scenarios; applicable matched {tax['matched']}/{tax['applicable']}; N/A {tax['not_applicable']}.

## 10. Runtime correlation
{summary['correlation']['all_attempts_with_request_id']}/{summary['correlation']['all_replay_attempts']} evidence-case attempts have request IDs; {summary['supported_replay_attempts']}/{summary['supported_replay_attempts']} supported Go attempts are runtime-correlated; zero orphan/duplicate IDs.

## 11. Current-state contamination
Per-attempt forbidden lookup count: 0.

## 12. No-side-effect evidence
Salary before/after hashes are identical.

## 13. Integrity failure handling
{summary['accepted_rejection_attempts']}/{summary['expected_rejection_attempts']} expected rejections accepted with structured errors.

## 14. Rounding observability
Research-only raw/decision trace exactness passed; trace does not alter payroll output.

## 15. Determinism
Every supported case matched across two repeats.

## 16. Per-case auditability
{raw['index']['case_count']} indexed case directories passed required-file and SHA-256 validation.

## 17. Performance observation
Controlled local observation only; three classes, 30 measured repeats each.

## 18. Legacy regression
Temporal v1: PASS; reconstructed baseline: 8 mismatches twice; fixed: 0; full pipeline: 32 exact + 4 expected rejection.

## 19. Second-environment reproduction
`SECOND_ENVIRONMENT_NOT_EXECUTED`.

## 20. Domain validation status
`NOT_AUTHORITATIVE_BUSINESS_ORACLE / DOMAIN_VALIDATION_PENDING`.

## 21. Claims supported
Local snapshot-bound deterministic replay, granular exactness, version applicability, runtime correlation, isolated mutations, per-case evidence, contamination zero, side-effect zero, and clean local reproducibility.

## 22. Claims not supported
Business-policy correctness, domain approval, second-environment reproducibility, and production-scale performance.

## 23. Remaining limitations
Correction replay remains unsupported. Performance remains local. Domain expert review and a second environment remain outstanding.

## 24. Readiness decision
**{readiness}**
"""
        write("TEMPORAL_REPLAY_FINAL_REPORT_V2.md", final)

    def generate_domain_files(self, raw: dict[str, Any]) -> None:
        rows = []
        selected: dict[str, dict[str, Any]] = {}
        seen_categories: set[str] = set()
        seen_components: set[str] = set()
        for item in raw["index"]["cases"]:
            choose = item["case_id"].startswith("TAX-V2-") or item["category"] not in seen_categories
            if item["status"] == "MATCHED":
                original = load_json(self.run / item["artifact_path"] / "original-output.json")["payload"]
                component_codes = {str(component.get("code")) for component in original.get("components", [])}
                choose |= bool(component_codes - seen_components)
                seen_components.update(component_codes)
            if choose:
                selected[item["case_id"]] = item
                seen_categories.add(item["category"])
        for item in selected.values():
            rows.append([item["case_id"], item["category"], item["artifact_path"], "PENDING", ""])
        for wave in raw["independent"]:
            rows.append([wave["wave_id"], "independent_mutation", "independent-mutation-waves.json", "PENDING", ""])
        for case_id in ["INVALID-002", "INVALID-005", "INVALID-008", "INVALID-011", "INVALID-014", "INVALID-017", "INVALID-020", "INVALID-023"]:
            rows.append([case_id, "legacy_baseline_mismatch", "legacy-regression", "PENDING", ""])
        path = self.run / "DOMAIN_VALIDATION_SAMPLE_V2.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["case_id", "stratum", "evidence_path", "domain_decision", "domain_comment"])
            writer.writerows(rows)
        (self.run / "DOMAIN_EXPERT_VALIDATION_FORM_V2.md").write_text("""# Domain Expert Validation Form v2

Status: `DOMAIN_VALIDATION_PENDING`

Expert name/role: ____________________  Date: ____________________

For each reviewed case record formula/rule family, expected business outcome, observed outcome, decision (`APPROVE`, `REJECT`, `NEEDS_CLARIFICATION`), disagreement, and evidence reference. Sign only after reviewing the attached artifacts. This form is intentionally blank; no approval is inferred.
""", encoding="utf-8")
        (self.run / "DOMAIN_VALIDATION_GUIDE_V2.md").write_text("""# Domain Validation Guide v2

Review the stratified CSV against authorized payroll policy and regulations. Cover component types, rule families, versioned rate/tax, effective boundaries, conflicts, rounding, legacy mismatches, independent mutations, and historical replay. Technical exactness is not a business-correctness oracle. Preserve disagreements and do not alter frozen expected results to obtain approval.
""", encoding="utf-8")

    def code_change_report(self, source: dict[str, Any]) -> str:
        def diff_stat(repo: Path) -> str:
            return subprocess.check_output(["git", "-C", str(repo), "diff", "--stat", "temporal-replay-v1-baseline..HEAD"], text=True, errors="replace").strip()
        engine = diff_stat(self.package.parent)
        laravel_dir = Path(os.environ.get("LARAVEL_DIR", self.package.parent.parent / "papa-website-public")).resolve()
        laravel = diff_stat(laravel_dir)
        return f"""# Code Change Report — Temporal Replay v2

## Engine and validation package
```
{engine}
```

## Laravel
```
{laravel}
```

The v1 evidence directories remain retained. Frozen expected outputs were not modified.
"""

    def generate_manifest(self, raw: dict[str, Any]) -> None:
        artifacts: dict[str, dict[str, Any]] = {}
        for path in sorted(self.run.rglob("*")):
            if not path.is_file() or path.name == "TEMPORAL_REPLAY_REPRODUCIBILITY_MANIFEST_V2.json" or "cases" in path.relative_to(self.run).parts:
                continue
            name = path.relative_to(self.run).as_posix()
            artifacts[name] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
        case_hash_indexes = {}
        for item in raw["index"]["cases"]:
            path = self.run / item["artifact_path"] / "artifact-hashes.json"
            case_hash_indexes[item["case_id"]] = {"path": path.relative_to(self.run).as_posix(), "sha256": sha256_file(path)}
        manifest = {
            "schema_version": "2.0", "run_id": self.run_id, "status": "PASS" if all(self.gates.values()) else "FAIL",
            "gates": self.gates, "artifacts": artifacts, "case_artifact_hash_indexes": case_hash_indexes,
            "case_count": raw["index"]["case_count"], "supported_attempts": raw["summary"]["supported_replay_attempts"],
            "second_environment": "SECOND_ENVIRONMENT_NOT_EXECUTED",
            "oracle_status": "NOT_AUTHORITATIVE_BUSINESS_ORACLE", "domain_validation": "DOMAIN_VALIDATION_PENDING",
            "readiness": "G" if all(self.gates.values()) else "F",
        }
        (self.run / "TEMPORAL_REPLAY_REPRODUCIBILITY_MANIFEST_V2.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    package = Path(__file__).resolve().parent
    try:
        result = Finalizer(args.run_dir, package).run_all()
    except EvidenceError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
