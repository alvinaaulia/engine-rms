# Failed Temporal Run

Status: **FAIL (preserved regression evidence)**.

The first envelope was rejected even after the Go encoder fix because Laravel's default HTTP JSON encoding changed numeric lexical form `0.0` to `0`, while the pre-transport hash used canonical JSON with preserved zero fractions.

Resolution: original capture, replay dispatch, and the experiment runner now send an explicit canonical JSON request body. The subsequent 408-case run passed.

