from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from differential_validation import finalize_clean_run


class CleanReproductionReportTests(unittest.TestCase):
    def test_report_is_derived_from_completed_run(self) -> None:
        manifest = {
            "runner_type": "WSL_NATIVE",
            "status": "PASS",
            "final_exit_code": 0,
            "clean_runner_id": "test-runner",
            "started_at": "2026-08-12T00:00:00Z",
            "finished_at": "2026-08-12T00:01:00Z",
            "total_duration_seconds": 60,
        }
        baseline = {"repeat_runs": [{"mismatch_count": 8}, {"mismatch_count": 8}]}
        fixed_manifest = {
            "commits": {"go": "go-commit", "laravel": "web-commit"},
            "results": {"cases": 624},
        }
        fixed_mismatch = {"mismatch_count": 0, "mismatched_case_count": 0}
        traces = [
            {
                "evaluation_category": "FULL_PAYROLL_PIPELINE",
                "status": "EXACT_MATCH",
                "persistence_asserted": True,
            },
            {
                "evaluation_category": "LARAVEL_CONFIGURATION_GUARD",
                "status": "EXPECTED_REJECTION",
                "persistence_asserted": False,
            },
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            clean = Path(temporary_directory)
            with patch.object(finalize_clean_run, "CLEAN", clean):
                finalize_clean_run.write_clean_reproduction_report(
                    manifest, baseline, fixed_manifest, fixed_mismatch, traces
                )
            report = (clean / "reports/CLEAN_REPRODUCTION_REPORT.md").read_text(encoding="utf-8")

        self.assertIn("status `PASS`", report)
        self.assertIn("0 mismatches across 0 cases", report)
        self.assertIn("1 exact matches; 1 persistence assertions", report)
        self.assertIn("Temporal replay v2 was not executed", report)
        self.assertNotIn("clean-environment reproduction was not executed", report.lower())


if __name__ == "__main__":
    unittest.main()
