# Temporal Payroll Replay Specification 1.0

## State model

- **Original execution** resolves current configuration exactly once for a payroll effective date, builds facts, creates canonical TPR-IR, invokes the engine, and atomically persists the salary, execution manifest, and output snapshot.
- **Execution manifest** is the immutable, versioned binding between facts, ruleset, component types, rule/rate/tax identities, rounding/hit policy, translator/engine compatibility, generated GRL, and original output.
- **Immutable artifact** is a locked manifest plus its one-to-one output. Normal application services must reject update/delete after lock.
- **Replay request** identifies a locked manifest and one of the supported verification modes. It never contains substitute current facts or configuration.
- **Replay result** contains the snapshot execution output, all bound version identities/hashes, deterministic output hash, differences, and structured status/failure.
- **Replay difference** is a path-addressed difference across components, summary, provenance, version bindings, facts/ruleset hashes, or output hash.

## Replay modes

| Mode | Meaning | Persistence |
|---|---|---|
| `VERIFICATION_SEMANTIC` | Re-execute canonical facts/ruleset and compare components, summary, provenance, versions, and hashes. Generated GRL bytes may differ only when a declared compatible translator produces the same semantic result. | replay run, differences, and audit only |
| `VERIFICATION_STRICT` | Semantic comparison plus exact translator/engine compatibility and generated-GRL hash equality. | replay run, differences, and audit only |
| `DRY_RUN` | Perform integrity/compatibility/execution/comparison and return a report without difference-row persistence; an audit/run record is still allowed. | replay control/audit tables only |

`CORRECTION` is explicitly unsupported in version 1. No replay mode may create or update a live salary.

## Failure semantics

| Failure | Required behavior |
|---|---|
| Unsupported manifest, TPR-IR, translator, or engine version | fail before execution with `REPLAY_SCHEMA_UNSUPPORTED` or an explicit compatibility failure |
| Missing rule/rate/tax binding when status is `BOUND` | fail with `REPLAY_VERSION_MISSING` |
| Corrupt facts, ruleset, GRL, manifest, or original output | fail before execution with `REPLAY_HASH_MISMATCH` or `REPLAY_MANIFEST_INVALID` |
| Forbidden current-state query | fail with `REPLAY_CURRENT_STATE_ACCESS_BLOCKED`; discard execution result |
| Engine/translator failure | fail with `REPLAY_EXECUTION_FAILED` |
| Successful execution with any strict/semantic difference | finish as mismatch with `REPLAY_OUTPUT_MISMATCH` and persist path-level differences |

## Invariants

- **TR-INV-001** Replay facts must equal the frozen facts snapshot. Enforced by canonical SHA-256 verification before the engine call.
- **TR-INV-002** Replay ruleset hash must equal the original ruleset hash.
- **TR-INV-003** Replay must not resolve current active rules.
- **TR-INV-004** Replay must not resolve current active rates.
- **TR-INV-005** Replay must not resolve current active tax configuration.
- **TR-INV-006** Verification replay must not mutate live payroll records.
- **TR-INV-007** A matching replay must have identical component, summary, provenance, version-binding, and output hashes. Net salary equality alone is insufficient.
- **TR-INV-008** Corrupt or incomplete artifacts must be rejected before execution.
- **TR-INV-009** Repeated replay of the same immutable manifest must be deterministic.
- **TR-INV-010** Historical rule/rate/tax version identities must be observable in the replay result.

## Current-state contamination definition

A replay is contaminated when it reads any live employee/master salary, profile, presence, overtime, leave, work schedule/config, active salary component, active/effective rule, active/effective rate, or active/effective tax source. Reading the immutable temporal tables, compatibility registry, authorization identity, and replay audit/control tables is permitted.

## No-side-effect guarantee

Replay code has no reference to salary persistence methods. Database query instrumentation rejects forbidden live-table reads. Tests compare live-table counts and canonical before/after hashes. Only `payroll_replay_runs`, `payroll_replay_differences`, and `payroll_replay_audit_logs` may change during verification.

## Canonicalization and decimals

Canonical JSON recursively sorts object keys, preserves array order, uses UTF-8 without insignificant whitespace, and preserves Unicode/slashes. Monetary values in temporal output artifacts are strings with exactly six decimal places. Hashes are lowercase SHA-256 hex. The manifest hash covers the locked manifest projection excluding only `manifest_sha256` itself.

## Semantic versus strict replay

Semantic replay still compares every output and provenance field. It relaxes only byte-identical generated GRL when the compatibility registry explicitly declares a compatible translator derivation. Strict replay requires the original translator and engine compatibility identifiers and the original generated-GRL SHA-256.

