# Temporal Compatibility Matrix

| Artifact | Supported value | Execution mode | Unknown value |
|---|---|---|---|
| Manifest | `1.0` | snapshot-only | `REPLAY_SCHEMA_UNSUPPORTED` |
| TPR-IR | `1.0` | typed TPR executor | `REPLAY_SCHEMA_UNSUPPORTED` |
| Translator | `laravel-go-tpr-translator-1.0` | exact registered translator contract | `REPLAY_SCHEMA_UNSUPPORTED` |
| Engine | `go-grule-tpr-engine-1.0` | GRULE snapshot execution | `REPLAY_SCHEMA_UNSUPPORTED` |
| Rounding | scale 6, `HALF_UP` | fixed-six output strings | `REPLAY_SCHEMA_UNSUPPORTED` |

Compatibility resolution is fail-closed. `migrateSnapshotForReadOnlyReplay` currently returns a derived, unchanged read-only snapshot only for TPR-IR 1.0. It never modifies the original snapshot or original hashes. No speculative migration for future schemas is registered.

