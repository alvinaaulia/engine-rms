# Temporal Replay Decision Log

| ID | Decision | Rationale | Consequence |
|---|---|---|---|
| TR-D001 | Keep V4 evidence immutable and create a new `runs/temporal-replay` namespace. | Temporal evidence must not rewrite the accepted differential baseline. | V4 hashes remain independently verifiable. |
| TR-D002 | Use the existing nested validation package rather than create `C:/PROJECT/differential_validation`. | The requested separate path does not exist and a copy would create competing provenance. | Temporal research artifacts live in `engine-rms/differential_validation`. |
| TR-D003 | Implement a separate snapshot-only replay path; do not add a flag that lets the current `execute()` resolver run during replay. | A mode flag inside current resolution is too easy to bypass accidentally. | Replay consumes only manifest snapshots and a dedicated Go envelope. |
| TR-D004 | Store large facts/ruleset/GRL/output snapshots in normalized temporal tables with one immutable manifest and one immutable output. | It keeps manifest indexing/version state separate from output payload size while preserving a one-to-one lock. | Exported manifest materializes both rows for schema validation. |
| TR-D005 | Treat rate/tax IDs as Laravel-resolved identities bound inside the hashed facts snapshot. | Rate and tax are resolved/calculated in Laravel before Go; Go cannot prove a database query it never performs. | Go derives and echoes those IDs from the hashed snapshot rather than trusting an unbound envelope field. |
| TR-D006 | Derive rule-version IDs from canonical TPR-IR rules, not only request metadata. | Rules are executed inside Go and directly identify their versions. | Replay rejects disagreement between envelope IDs and snapshot rules. |
| TR-D007 | Use scale-6 decimal strings in temporal artifacts. | Existing TPR policy is scale 6 HALF_UP and binary floats are unsuitable as immutable money evidence. | Comparators compare canonical decimal strings. |
| TR-D008 | Permit an empty rate/tax ID list only with explicit `NOT_APPLICABLE` binding status. | Empty and missing are semantically different. | `BOUND` with an empty list is a structured failure. |
| TR-D009 | Verification replay may write audit/control rows but never salary/configuration rows. | A completely write-free operation would prevent durable audit evidence. | No-side-effect tests whitelist only replay tables. |
| TR-D010 | Defer correction replay. | Correctness and read-only verification are prerequisite. | No code path updates active payroll from replay output. |
| TR-D011 | Preserve original generated GRL and its hash, but regenerate it from the snapshot during replay. | Storing only GRL would lose the typed source; storing only TPR-IR would prevent strict translator verification. | Strict mode compares regenerated GRL hash; semantic mode requires explicit compatibility. |
| TR-D012 | Original salary, manifest, and output become visible atomically in one database transaction. | A locked orphan or salary without binding is unacceptable. | Any persistence/validation failure rolls back all database rows. |

