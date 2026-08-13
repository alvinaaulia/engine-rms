from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PACKAGE = Path(__file__).resolve().parents[1]


class ResearchPathTest(unittest.TestCase):
    def test_run_evidence_honors_explicit_public_laravel_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            expected = Path(directory).resolve()
            module_path = PACKAGE / "generate_run_evidence.py"
            spec = importlib.util.spec_from_file_location("generate_run_evidence_path_test", module_path)
            self.assertIsNotNone(spec)
            self.assertIsNotNone(spec.loader)
            module = importlib.util.module_from_spec(spec)
            with patch.dict(os.environ, {"LARAVEL_DIR": str(expected)}):
                spec.loader.exec_module(module)
            self.assertEqual(expected, module.LARAVEL)

    def test_active_research_automation_has_no_legacy_repository_path(self) -> None:
        sources = [
            PACKAGE / relative
            for relative in (
                "run_all.sh",
                "clean_validate.sh",
                "differential_runner/laravel_tpr_bridge.php",
                "generate_run_evidence.py",
                "generate_hardening_artifacts.py",
                "generate_clean_closure.py",
                "generate_v4_clean_execution.py",
                "generate_v4_runner_closure.py",
                "package_artifact.py",
                "finalize_temporal_v2.py",
                "Dockerfile.laravel",
                "docker-compose.yml",
            )
        ]
        offenders = [
            path.relative_to(PACKAGE).as_posix()
            for path in sources
            if "papa-website-v2" in path.read_text(encoding="utf-8", errors="replace")
        ]
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
