# Temporal Replay Evidence Closure v2 — Source Baseline

## Freeze decision

Temporal Replay v1 is frozen as the immutable input to Evidence Closure v2. The canonical validation package is `C:\PROJECT\engine-rms\differential_validation`; the separately stated path `C:\PROJECT\differential_validation` does not exist in this workspace.

| Repository / package | v1 baseline commit | Baseline tag | v2 branch | Dirty before freeze |
|---|---|---|---|---|
| Go engine and canonical validation package | `96240c0e0ce3d6da599c2eea49ad461e8bf637e6` | `temporal-replay-v1-baseline` | `feature/temporal-replay-evidence-closure-v2` | No |
| Laravel application | `a026abb0ca17480f72b38176eef50bbd1fb52911` | `temporal-replay-v1-baseline` | `feature/temporal-replay-evidence-closure-v2` | No |

The annotated tag in each repository resolves to the commit shown above. Existing Temporal Replay v1 runs and legacy V4 evidence remain retained and must not be overwritten.

## Primary v1 evidence

The clean v1 run is `runs/temporal-replay/temporal-clean-20260802T160000Z`. Its source identity records Go source commit `ba568d718dd9b9c50659b0ab4a106e2c80314ddf` and Laravel commit `a026abb0ca17480f72b38176eef50bbd1fb52911`; engine commit `96240c0e0ce3d6da599c2eea49ad461e8bf637e6` adds only the recorded clean evidence.

## Domain status at freeze

`NOT_AUTHORITATIVE_BUSINESS_ORACLE / DOMAIN_VALIDATION_PENDING`

No domain approval, second-environment result, or production-scale performance claim is implied by this freeze.
