# Current research evidence

This file is the canonical entry point for reviewers. Historical reports remain
in the repository only for provenance and must not be combined with current
claims unless their recorded source commits match the article.

## Current commit-bound CI verification

- Status: `PASS`
- GitHub Actions run: `31848223965`
- Engine commit: `76112316d1e56044e53cd65baf6409a0fd00bb18`
- Laravel commit: `8b7f060aff27b79984a730e4c04535845843bc1e`
- Branch: `feature/sinta3-system-readiness-20260812`
- Runtime: Go 1.26.6, PHP 8.4, Python 3.14, MySQL 8.4.5
- Passed gates: Go tests, Go vet, Go vulnerability scan, Laravel tests,
  Composer audit, npm audit/build, desktop browser accessibility smoke
  tests, differential evidence pipeline, and commit-bound Go statement coverage
- Published artifact: `differential-validation-evidence` (GitHub artifact ID
  `9236681519`, retained until 2026-11-12)

Run URL: <https://github.com/alvinaaulia/engine-rms/actions/runs/31848223965>

The paired commits and published provenance tags are verified inside the run.
The CI-generated artifact is authoritative for claims about these two commits.

## Latest WSL clean reproduction

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
are authoritative for these numbers. This run predates the current CI pair and
is retained as historical clean-environment evidence, not silently relabelled
as evidence for the newer commits.

## Coverage status

- Commit-bound Go statement coverage is generated and published by the current
  CI run.
- The local engine-code verification measured 85.9% Go statement coverage;
  subsequent engine commits in the current pair change only CI/finalizer code.
- The last completed condition-coverage result was 98.94%, but it belongs to an
  earlier source state.
- A Gobco v1.3.4 rerun was stopped without a final report to avoid competing
  with the resource-intensive replay on the research laptop. Therefore 98.94%
  must not be attributed to the current commit and condition coverage remains
  a non-blocking supplementary metric.

## Temporal replay evidence

- Status: `CURRENT_SOURCE_CI_PASS`
- GitHub Actions run: `31848223965`
- Source pair: engine `76112316d1e56044e53cd65baf6409a0fd00bb18`;
  Laravel `8b7f060aff27b79984a730e4c04535845843bc1e`
- Published artifact: `temporal-replay-v2-current-source` (GitHub artifact ID
  `9236717112`, retained until 2026-11-12, digest
  `sha256:3538500a44335f70254a8909163dd8a51c06d8d041388cf46ff3c9210f2b47ae`)
- Result: the current-source Temporal Replay v2 collector, artifact finalizer,
  provenance report, and all replay gates completed successfully on a clean
  Ubuntu GitHub runner with MySQL 8.4.5.

The artifact above is authoritative for the detailed current-source counts and
hashes. The earlier Windows/WSL two-environment comparison remains historical
evidence for engine `0f756ce...` and Laravel `aa6b05f...`; it must not be
silently relabelled as a comparison for the newer commits. The current clean CI
pass closes the source-bound technical replay gate, but not the separate
domain-expert validation gate.

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

## Readiness changes verified

The post-run hardening branch upgrades Go to 1.26.6, removes reachable Go
vulnerabilities, repairs the public CI route, aligns browser/accessibility tests
with the supported desktop UI, makes execution/replay timeouts configurable,
and hardens Temporal Replay diagnostics and provenance fallback. These changes
passed the commit-bound CI run identified above. Authorized domain-expert review
remains required before making business-policy correctness claims in an article.
