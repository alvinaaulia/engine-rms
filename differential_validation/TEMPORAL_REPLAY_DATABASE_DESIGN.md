# Temporal Replay Database Design

## Tables

### `payroll_execution_manifests`

One immutable row per original salary execution. It contains execution/salary/employee identity, payroll period, manifest/schema/translator/engine versions, facts and ruleset snapshots/hashes, component type snapshot, sorted rule/rate/tax version IDs and binding status, rounding/hit policy, generated GRL/hash, original output hash, manifest hash, execution time, and lock time.

Indexes: unique execution UUID, unique salary ID, employee plus period, ruleset hash, original output hash, executed time. Foreign keys restrict deletion of user and salary while a manifest exists.

### `payroll_execution_outputs`

One-to-one immutable output for a manifest: component, summary, provenance, raw engine response snapshots and the canonical output hash. The row is created before its manifest is locked and cannot be updated/deleted afterward through normal models.

### `payroll_replay_runs`

One replay attempt with UUID, manifest, verification mode, actor/reason, lifecycle status, original/replay hashes, difference count, start/finish timestamps, structured failure, latency, and query count. It never points to a newly created salary.

### `payroll_replay_differences`

Path-level comparison output containing category/type, original and replay values as JSON, and severity. Indexed by replay run and category/path.

### `payroll_replay_audit_logs`

Append-only replay lifecycle audit with actor, action, metadata, and occurrence time.

## JSON usage

JSON is appropriate for immutable hierarchical facts, TPR-IR, component map, policies, version arrays, engine responses, and path-level values. Queryable identity/status/time/hash fields remain scalar and indexed. Money inside JSON is always a decimal string; scalar performance fields use integer microseconds/bytes rather than floating point.

## Transaction boundaries

Original capture uses one database transaction for salary, manifest, output, manifest validation, and lock. A failure rolls back all rows. External Go execution occurs before the persistence transaction and has no application database side effect.

Replay integrity is checked before the Go call. Replay control/audit rows are intentionally durable. The live salary and all payroll configuration tables are outside the replay write set.

## Immutability

Eloquent model guards reject updates/deletes when `locked_at` is set. Output guards consult the parent lock. Application routes expose no manifest update/delete operation. Database users for future dedicated replay runners should receive SELECT on immutable source tables and INSERT/UPDATE only on replay control tables.

