# Failed Temporal Run

Status: **FAIL (preserved regression evidence)**.

The first envelope was rejected because Go's canonical JSON encoder HTML-escaped comparison operator `>` while Laravel did not. The expected and actual ruleset hashes are preserved in `raw-logs/experiment-command.log`; the exact envelope and Laravel canonical ruleset are preserved beside it.

Resolution: Go canonical hashing now uses `SetEscapeHTML(false)`. Regression: `TestCanonicalSHA256DoesNotHTMLEscapeComparisonOperators`.

