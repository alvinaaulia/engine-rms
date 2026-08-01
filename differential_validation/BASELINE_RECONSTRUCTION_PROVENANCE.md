
# Baseline reconstruction provenance

Baseline type: `RECONSTRUCTED`. Original historical raw output is unavailable. The fixed source was rebuilt with the non-production `differential_baseline` tag, which disables only the remediated runtime type check. The reconstruction was run 2 times and reproduced 8 stable mismatching case IDs: INVALID-002, INVALID-005, INVALID-008, INVALID-011, INVALID-014, INVALID-017, INVALID-020, INVALID-023.

| Repeat | Mismatch | Semantic result hash | Raw command evidence |
|---|---|---|---|
| 1 | 8 | 4a1d6b5941e7fa7747eb5888d80c83d61988797c772fdbf6c7edc12910930317 | runs/reconstructed-baseline/repeat-1/raw-logs/differential.meta.json |
| 2 | 8 | 4a1d6b5941e7fa7747eb5888d80c83d61988797c772fdbf6c7edc12910930317 | runs/reconstructed-baseline/repeat-2/raw-logs/differential.meta.json |

Corpus, expected-result, and policy hashes are `08f16457e2ba3a3ce614ba4e71d9d2629f496c9249c43fe6b09828618161f011`, `e6d5a74fef5b739134796bb83b41641d155160d16fe563276fc4f57940d9e91c`, and `1edaaed6094facf558de01e741f12beb0ac3a828d950c2d7ab8e58d2da9ddca1`. Method, limitations, patch, and source state are in `runs/reconstructed-baseline/`.
