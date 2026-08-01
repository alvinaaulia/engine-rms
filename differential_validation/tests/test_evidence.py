from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from differential_validation.evidence import EvidenceError, PARSER_VERSION, parse_exit_status, parse_go_test, parse_junit


class EvidenceParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def meta(self, evidence: Path, exit_code: int = 0) -> Path:
        now = datetime.now(timezone.utc).isoformat()
        path = self.root / "command.meta.json"
        path.write_text(json.dumps({
            "evidence_file": evidence.name,
            "parser_version": PARSER_VERSION,
            "command": ["test-command"],
            "exit_code": exit_code,
            "started_at": now,
            "finished_at": now,
            "duration_seconds": 0,
        }), encoding="utf-8")
        return path

    def test_missing_log_is_rejected(self) -> None:
        missing = self.root / "missing.log"
        with self.assertRaises(EvidenceError):
            parse_exit_status(self.meta(missing))

    def test_malformed_go_log_is_rejected(self) -> None:
        evidence = self.root / "go.json"
        evidence.write_text("not-json\n", encoding="utf-8")
        with self.assertRaises(EvidenceError):
            parse_go_test(self.meta(evidence))

    def test_failed_command_cannot_be_reported_as_pass(self) -> None:
        evidence = self.root / "status.txt"
        evidence.write_text("looks fine", encoding="utf-8")
        self.assertEqual("FAIL", parse_exit_status(self.meta(evidence, exit_code=7))["status"])

    def test_inconsistent_junit_count_is_rejected(self) -> None:
        evidence = self.root / "junit.xml"
        evidence.write_text('<testsuite tests="2" failures="0"><testcase name="one"/></testsuite>', encoding="utf-8")
        with self.assertRaises(EvidenceError):
            parse_junit(self.meta(evidence))

    def test_stale_metadata_is_rejected(self) -> None:
        evidence = self.root / "status.txt"
        evidence.write_text("new evidence", encoding="utf-8")
        meta = self.meta(evidence)
        old = evidence.stat().st_mtime - 10
        os.utime(meta, (old, old))
        with self.assertRaises(EvidenceError):
            parse_exit_status(meta)

    def test_missing_evidence_has_no_hard_coded_fallback(self) -> None:
        with self.assertRaises(EvidenceError):
            parse_junit(self.root / "never-executed.meta.json")


if __name__ == "__main__":
    unittest.main()
