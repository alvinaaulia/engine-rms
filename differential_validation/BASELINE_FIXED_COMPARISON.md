
# Baseline versus fixed

| Stage | Laravel commit | Go commit | Cases | Mismatch | Result |
|---|---|---|---|---|---|
| Baseline (reconstructed) | ca16f0500d8404cecaca03950cfc252072ca3e23 | 1dcad9df1be852263590fd23ab11ce569ea1c99e | 624 | 8 | FAIL |
| Fixed | 4f2e402b07811ae90f846cdcc3c7d9f6df5bd411 | 8f98a3bed58f204e0f9094fe3c1139ab8bb8e41e | 624 | 0 | PASS |

The original eight-mismatch raw output had been overwritten before this remediation. It is not presented as original evidence. The baseline is labeled `RECONSTRUCTED_BASELINE` and was executed with the preserved pre-fix runtime-type behavior behind the non-production `differential_baseline` build tag. The fixed run used the same frozen corpus and expected results.
