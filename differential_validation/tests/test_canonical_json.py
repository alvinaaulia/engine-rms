from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from differential_validation.canonical_json import encode_frozen_json


ROOT = Path(__file__).resolve().parents[1]


class CanonicalFrozenJsonTests(unittest.TestCase):
    def test_frozen_corpus_and_expected_use_platform_independent_bytes(self) -> None:
        frozen = json.loads((ROOT / "FROZEN_ARTIFACT_MANIFEST.json").read_text(encoding="utf-8"))
        for filename, hash_key in (
            ("oracle_input_cases.json", "corpus_sha256"),
            ("oracle_expected_results.json", "expected_results_sha256"),
        ):
            path = ROOT / filename
            canonical = encode_frozen_json(json.loads(path.read_text(encoding="utf-8")))
            self.assertEqual(canonical, path.read_bytes())
            self.assertEqual(frozen[hash_key], hashlib.sha256(canonical).hexdigest())
            self.assertNotIn(b"\n", canonical.replace(b"\r\n", b""))

    def test_independent_verification_timestamp_is_frozen(self) -> None:
        freeze = json.loads((ROOT / ".oracle_frozen.json").read_text(encoding="utf-8"))
        expected = json.loads((ROOT / "oracle_expected_results.json").read_text(encoding="utf-8"))
        timestamps = {
            result["verification_timestamp"]
            for result in expected["results"]
            if result["verification_status"] == "INDEPENDENTLY_VERIFIED"
        }
        self.assertEqual({freeze["verification_timestamp"]}, timestamps)


if __name__ == "__main__":
    unittest.main()
