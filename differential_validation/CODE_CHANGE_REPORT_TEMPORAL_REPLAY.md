# Code Change Report: Temporal Payroll Replay

## Laravel

- Added five temporal persistence tables, immutable Eloquent models, canonical JSON storage cast, compatibility registry, integrity validator, comparator, contamination guard, replay service, API controller, routes, and authorization policy.
- Integrated temporal capture into salary creation with a single persistence transaction and transfer-proof cleanup on failure.
- Added rate/tax resolution identities to the hashed facts and temporal response provenance.
- Added unit, persistence, corruption, no-side-effect, and real Laravel-to-Go replay tests.
- Added the guarded 408-case experiment command.

## Go

- Added `/replay`, strict envelope decoding, snapshot/hash/version validation, snapshot-only TPR execution, fixed-six money output, generated-GRL verification, provenance, and structured failures.
- Added deterministic, corruption, compatibility, version-binding, and canonical hash regression tests.
- Aligned canonical JSON with Laravel by disabling HTML escaping during hashing.

## Validation package

- Added architecture/audit/specification/schema/database documents.
- Added version, safety, compatibility, contamination, and change reports.
- Added a no-Docker clean temporal runner, finalizer, Make target, run-scoped raw logs, manifests, results, reports, and reproducibility manifest.

## Bugs found by validation

1. MySQL JSON normalization changed numeric lexical forms and invalidated persisted snapshot hashes. Facts and rulesets now use canonical JSON text casts.
2. Go HTML escaping of comparison operators differed from Laravel canonical JSON. Go canonical encoding now disables HTML escaping.
3. Default Laravel HTTP JSON encoding collapsed `0.0` to `0`. Temporal envelopes are now sent as an explicit canonical JSON body.

Each issue has regression coverage or is exercised by the real cross-language temporal experiment.

