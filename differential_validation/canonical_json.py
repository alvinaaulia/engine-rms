"""Canonical byte encoding for artifacts whose SHA-256 was frozen on Windows."""

from __future__ import annotations

import json


def encode_frozen_json(payload: object) -> bytes:
    """Serialize frozen JSON with deterministic CRLF bytes on every platform."""
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    return text.replace("\n", "\r\n").encode("utf-8")
