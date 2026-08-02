# Version Observability Report

## Implemented binding path

The original Laravel execution resolves rate rows and company-tax rows before the Go call. `PayrollRuleEngineService` now records the selected row IDs and version metadata in `facts.source.resolved_rate_version_ids`, `resolved_rate_versions`, `resolved_tax_version_ids`, and `resolved_tax_versions`. These fields are part of the canonical facts snapshot and therefore part of `facts_sha256`.

The canonical TPR-IR ruleset supplies rule-version IDs. Go derives rule IDs from the hashed ruleset and rate/tax IDs from the hashed facts rather than accepting unverified envelope values. It rejects disagreement with `REPLAY_VERSION_MISSING`.

The response provenance exposes:

- rule, rate, and tax version IDs;
- facts and ruleset SHA-256;
- translator and engine compatibility versions;
- request ID and execution UUID.

Laravel validates that response provenance equals the locked manifest before capture and again before replay. Empty rate or tax arrays require explicit `NOT_APPLICABLE`; rules always require `BOUND`.

## Evidence

The temporal experiment records 404 supported manifests and 808 exact replay attempts with version comparison enabled. Four targeted negative cases exercise corrupt facts, missing rule-version identity, unsupported schema, and missing output. Domain-policy approval remains `DOMAIN_VALIDATION_PENDING`.

