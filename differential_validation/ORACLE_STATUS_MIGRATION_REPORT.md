
# Oracle status migration report

The previous blanket use of `ADJUDICATED` was invalid and has been removed. Status is now attached per case with verifier identity, method, timestamp, adjudication reference, and notes.

| Verification status | Cases |
|---|---|
| INDEPENDENTLY_VERIFIED | 89 |
| POLICY_DERIVED | 535 |

No row is adjudicated without written evidence. The frozen artifact remains `FROZEN_REFERENCE_ORACLE` and is explicitly not an authoritative business oracle. Frozen expected hash: `e6d5a74fef5b739134796bb83b41641d155160d16fe563276fc4f57940d9e91c`.
