# Current research evidence

This file is the canonical entry point for reviewers. Historical reports remain
in the repository only for provenance and must not be combined with current
claims unless their recorded source commits match the article.

## Current clean reproduction

- Status: `PASS`
- Runner: WSL-native Ubuntu, without Docker
- Run: `runs/clean-environment/wsl-clean-20260812T174634Z`
- Cases: 624
- Reconstructed baseline: 8 mismatches in the same 8 cases on both repeats
- Fixed implementation: 0 mismatches across 6,840 comparisons
- Full Laravel suite: 169 tests, 1,638 assertions, 0 failures
- Full-pipeline test: 750 assertions, 0 failures
- Artifact validator: 28 artifacts, `PASS`

The run manifest and `reports/CLEAN_REPRODUCTION_REPORT.md` inside that directory
are authoritative for these numbers.

## Temporal replay evidence

The completed two-environment Temporal Replay v2 comparison is stored at
`runs/temporal-replay-v2/SECOND_ENVIRONMENT_TEMPORAL_V2_COMPARISON.md`. It is
valid only for the engine and Laravel commits recorded in that report. A new
current-source replay must replace this note before an article attributes the
temporal result to later source revisions.

## Domain claim boundary

`DOMAIN_VALIDATION_STATUS.md` is authoritative. Technical equivalence against
the frozen reference oracle is not authoritative confirmation of company,
payroll, tax, or legal policy. Domain-expert decisions and signature must remain
pending until supplied by an authorized person.

## Required release gates

1. Unit, integration, browser, dependency, and vulnerability gates pass.
2. CI records the paired engine and Laravel commit identities.
3. Generated coverage and clean-run evidence identify the tested source commit.
4. Article claims quote only an evidence run bound to those source identities.

## Readiness changes awaiting a new evidence run

The post-run hardening branch upgrades Go to 1.26.5, removes reachable Go
vulnerabilities, repairs the public CI route, and adds browser/accessibility
gates. These changes have passed local source and integration tests, but they do
not replace the clean reproduction above until CI creates a new manifest whose
source identities include the readiness commits.
