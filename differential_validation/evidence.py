"""Strict parsers for command evidence consumed by report generation."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

PARSER_VERSION = "2.0"
REQUIRED_META = {
    "evidence_file", "parser_version", "command", "exit_code",
    "started_at", "finished_at", "duration_seconds",
}


class EvidenceError(RuntimeError):
    pass


def _timestamp(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError(f"malformed timestamp: {value}") from exc


def load_meta(meta_path: Path) -> tuple[dict, Path]:
    if not meta_path.exists():
        raise EvidenceError(f"missing metadata: {meta_path}")
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise EvidenceError(f"malformed metadata: {meta_path}") from exc
    missing = REQUIRED_META - set(meta)
    if missing:
        raise EvidenceError(f"metadata missing fields {sorted(missing)}: {meta_path}")
    if meta["parser_version"] != PARSER_VERSION:
        raise EvidenceError(f"unsupported parser version: {meta['parser_version']}")
    evidence_path = (meta_path.parent / meta["evidence_file"]).resolve()
    if not evidence_path.exists():
        raise EvidenceError(f"missing evidence file: {evidence_path}")
    started = _timestamp(meta["started_at"])
    finished = _timestamp(meta["finished_at"])
    if finished < started or float(meta["duration_seconds"]) < 0:
        raise EvidenceError(f"inconsistent timing metadata: {meta_path}")
    if evidence_path.stat().st_mtime > meta_path.stat().st_mtime + 1:
        raise EvidenceError(f"stale metadata for evidence file: {evidence_path}")
    return meta, evidence_path


def parse_junit(meta_path: Path) -> dict:
    meta, evidence_path = load_meta(meta_path)
    try:
        root = ElementTree.parse(evidence_path).getroot()
    except (ElementTree.ParseError, OSError) as exc:
        raise EvidenceError(f"malformed JUnit XML: {evidence_path}") from exc
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    if not suites:
        raise EvidenceError(f"JUnit XML contains no test suites: {evidence_path}")
    totals = {key: sum(int(suite.attrib.get(key, 0)) for suite in suites) for key in ("tests", "failures", "errors", "skipped", "assertions")}
    observed_cases = sum(len(suite.findall(".//testcase")) for suite in suites)
    if observed_cases != totals["tests"]:
        raise EvidenceError(f"inconsistent JUnit test count: declared {totals['tests']}, observed {observed_cases}")
    totals["duration_seconds"] = sum(float(suite.attrib.get("time", 0)) for suite in suites)
    totals["passed"] = totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"]
    totals["status"] = "PASS" if meta["exit_code"] == 0 and totals["failures"] == 0 and totals["errors"] == 0 else "FAIL"
    totals["evidence"] = meta
    return totals


def parse_go_test(meta_path: Path) -> dict:
    meta, evidence_path = load_meta(meta_path)
    tests: dict[tuple[str, str], str] = {}
    package_failures = set()
    duration = 0.0
    try:
        lines = evidence_path.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EvidenceError(f"malformed Go JSON event at line {number}: {evidence_path}") from exc
            action = event.get("Action")
            package = event.get("Package", "")
            test = event.get("Test")
            if test and action in {"pass", "fail", "skip"}:
                tests[(package, test)] = action
            if not test and action == "fail":
                package_failures.add(package)
            if not test and action == "pass":
                duration += float(event.get("Elapsed", 0))
    except OSError as exc:
        raise EvidenceError(f"cannot read Go evidence: {evidence_path}") from exc
    counts = {state: sum(1 for value in tests.values() if value == state) for state in ("pass", "fail", "skip")}
    return {
        "tests": len(tests), "passed": counts["pass"], "failed": counts["fail"], "skipped": counts["skip"],
        "package_failures": len(package_failures), "duration_seconds": duration,
        "status": "PASS" if meta["exit_code"] == 0 and counts["fail"] == 0 and not package_failures else "FAIL",
        "evidence": meta,
    }


def parse_exit_status(meta_path: Path) -> dict:
    meta, _ = load_meta(meta_path)
    return {"status": "PASS" if meta["exit_code"] == 0 else "FAIL", "evidence": meta}
