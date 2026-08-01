# Attempt termination notice

The validation-runner was intentionally stopped after the second, in-container `git status --porcelain` scan of the Laravel snapshot remained active for approximately 15 minutes on the Windows/Linux bind mount. Source commits and clean status had already been verified on the host immediately before the self-contained clones were mutated for isolated outputs.

Exit code `143` records that termination. No migration, baseline, fixed differential, translator, Go test, Laravel test, E2E, guard, schema, hash, or report command had started. Those stages therefore remain `NOT_EXECUTED` for this attempt.

The next source revision skips the redundant status scan only when `SOURCE_SNAPSHOT_VERIFIED=1`; normal local execution continues to reject dirty repositories.
