
# Baseline versus fixed

| Stage | Laravel commit | Go commit | Cases | Mismatch | Result |
|---|---|---|---|---|---|
| Baseline (reconstructed) | ca16f0500d8404cecaca03950cfc252072ca3e23 | 1dcad9df1be852263590fd23ab11ce569ea1c99e | 624 | 8 | FAIL |
| Fixed | 0b437d6af1f99729bffb5bac6a55c40cc079d023 | 10b429c5011b47d4db932a11c51c84115eaeb868 | 624 | 0 | PASS |

The original eight-mismatch raw output had been overwritten before this remediation. It is not presented as original evidence. The baseline is labeled `RECONSTRUCTED_BASELINE` and was executed with the preserved pre-fix runtime-type behavior behind the non-production `differential_baseline` build tag. The fixed run used the same frozen corpus and expected results.
