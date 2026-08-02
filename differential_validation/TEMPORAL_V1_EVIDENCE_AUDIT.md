# Temporal Replay v1 Evidence Audit

## Scope and method

This audit reads the raw files in `runs/temporal-replay/temporal-clean-20260802T160000Z`. Counts below were recalculated from JSON/JSONL and exit-code files; they were not copied from the narrative report.

| Claim | Value | Raw evidence | Generator | Status |
|---|---:|---|---|---|
| Manifest count | 408 lines; 408 unique execution UUIDs and manifest hashes | `temporal-execution-manifests.jsonl` | Laravel temporal experiment | VERIFIED |
| Replay attempt count | 816 unique `(case_id, repeat)` records | `replay-results.jsonl` | Laravel temporal experiment | VERIFIED |
| Supported exact replay | 808 `MATCHED`; 0 difference artifacts | `replay-results.jsonl`, `replay-differences.json` | Replay service / experiment | VERIFIED at aggregate output-hash level |
| Expected rejection | 8 `EXPECTED_REJECTION` | `replay-results.jsonl` | Laravel temporal experiment | VERIFIED |
| Manifest request IDs | 408 present and unique | manifest `original_provenance.request_id` | Go original response / Laravel capture | VERIFIED for original execution |
| Runtime replay request IDs | Not stored in replay result records | `replay-results.jsonl` | v1 experiment | MISSING |
| Go runtime correlation in E2E | 36 `go_request_id = null`; 32 `NOT_OBSERVABLE`, 4 rejected before HTTP | `full-pipeline-e2e.json` | Laravel E2E test | NOT_VERIFIED |
| Go internal runtime trace | 32 source-verified only; 4 not applicable | `full-pipeline-e2e.json` | Laravel E2E test | NOT_VERIFIED |
| Rule/rate/tax binding in temporal manifests | All 408 report `BOUND` with non-empty IDs | manifests | Laravel capture / Go replay validation | VERIFIED for the synthetic temporal dataset |
| Tax applicability in full pipeline | 32 manual override and 4 rejected before execution; all tax ID lists empty | `full-pipeline-e2e.json` | Laravel full-pipeline test | NOT_APPLICABLE; must not be counted as matched |
| Granular exactness denominators | Only aggregate `exact_match_percent` is present | `experiment-summary.json` | Laravel temporal experiment | MISSING |
| Per-case comparator result | Replay rows contain status, output hash, difference count, and query count only | `replay-results.jsonl` | Laravel temporal experiment | PARTIALLY_VERIFIED |
| Independent mutation effects | No reset between waves; waves 5–7 inherit prior state | `mutation-waves.json` and command source | Laravel temporal experiment | NOT_VERIFIED |
| Cumulative mutation effects | 7 sequential mutations, state/result changed, sentinel matched | `mutation-waves.json` | Laravel temporal experiment | VERIFIED as cumulative only |
| Current-state contamination | Aggregate query count is zero; no per-case trace artifact | replay rows / summary | Laravel query guard | PARTIALLY_VERIFIED |
| Salary side effects | Before/after salary-state SHA-256 equal | `experiment-summary.json` | Laravel temporal experiment | VERIFIED |
| Time provenance | Folder ID encodes `160000Z`; source start is `15:28:15Z`; experiment start is `15:37:11Z`; summary has no `run_id` | folder, `source-identity.json`, `experiment-summary.json` | clean runner / experiment | INCONSISTENT |
| Command exits | 15 recorded exit-code files, all zero | `raw-logs/*.exit-code.txt` | clean runner | VERIFIED |
| Second environment | No independent hosted/VM/second-machine raw run | package contents | N/A | MISSING |
| Domain validation | Explicitly pending | summary/final report | finalizer | VERIFIED as pending |

## Confirmed closure requirements

1. Preserve v1 evidence and treat the seven original waves as `CUMULATIVE_MUTATION_WAVES` only.
2. Generate independent waves from one restored, verified baseline state.
3. Emit numerator, denominator, applicability, missing, and mismatch evidence from per-attempt comparator records.
4. Separate tax `NOT_APPLICABLE` from `APPLICABLE_MATCHED`.
5. Instrument runtime Laravel → HTTP → Go → translator → GRULE correlation.
6. Derive the run ID from the canonical UTC start instant and validate consistency.
7. Emit schema-valid per-case artifacts, per-case forbidden-lookup traces, side-effect checks, and hashes.
8. Keep performance claims limited to controlled local observation and domain status pending unless external evidence exists.
