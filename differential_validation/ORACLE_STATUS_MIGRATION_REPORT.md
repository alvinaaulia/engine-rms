
# Oracle status migration report

The previous blanket use of `ADJUDICATED` was invalid and has been removed. Status is now attached per case with verifier identity, method, timestamp, adjudication reference, and notes.

| Verification status | Cases |
|---|---|
| INDEPENDENTLY_VERIFIED | 89 |
| POLICY_DERIVED | 535 |

No row is adjudicated without written evidence. The frozen artifact remains `FROZEN_REFERENCE_ORACLE` and is explicitly not an authoritative business oracle. Frozen expected hash: `35d7c1d4ccd62db3370b9c561b2497977bf99df120b43074e1ac7122fe3a372a`.
