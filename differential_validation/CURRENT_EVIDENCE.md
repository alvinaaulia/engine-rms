# Current research evidence

This file is the canonical entry point for reviewers. Historical reports remain
in the repository only for provenance and must not be combined with current
claims unless their recorded source commits match the article.

## Current commit-bound CI verification

- Status: `PASS`
- GitHub Actions run: `31733636295`
- Engine commit: `0f756cecb16a6271f24c3de239319a684807eaf5`
- Laravel commit: `aa6b05f9d62cc277decc59cc44745ada5e56ccae`
- Branch: `feature/sinta3-system-readiness-20260812`
- Runtime: Go 1.26.5, PHP 8.4, Python 3.14, MySQL 8.4.5
- Passed gates: Go tests, Go vet, Go vulnerability scan, Laravel tests,
  Composer audit, npm audit/build, desktop/mobile browser accessibility smoke
  tests, differential evidence pipeline, and commit-bound Go statement coverage
- Published artifact: `differential-validation-evidence` (GitHub artifact ID
  `9194289013`, retained until 2026-11-11)

Run URL: <https://github.com/alvinaaulia/engine-rms/actions/runs/31733636295>

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
- The last completed condition-coverage result was 98.94%, but it belongs to an
  earlier source state.
- A Gobco v1.3.4 run against the current commit exceeded the 15-minute local
  execution limit without producing a final report. Therefore 98.94% must not
  be attributed to the current commit and condition coverage is not a blocking
  CI gate.

## Temporal replay evidence

- Status: `SECOND_ENVIRONMENT_PASS`
- Primary Windows run:
  `runs/temporal-replay-v2/temporal-v2-20260813T195025Z-9379cd45`
- Secondary Linux WSL 2 native run, without Docker:
  `runs/temporal-replay-v2/temporal-v2-20260813T211003Z-a7304d0d`
- Cross-environment comparison:
  `runs/temporal-replay-v2/CURRENT_SOURCE_SECOND_ENVIRONMENT_COMPARISON.md`
- Source pair: engine `0f756cecb16a6271f24c3de239319a684807eaf5`;
  Laravel `aa6b05f9d62cc277decc59cc44745ada5e56ccae`
- Result in each environment: 418 cases, 824/824 supported attempts matched,
  12/12 expected rejections accepted, 30,536/30,536 payload envelopes passed,
  and zero cross-environment comparator hash mismatches.

This closes the current-source second-environment technical reproduction gate.
It does not close the separate domain-expert validation gate.

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

The post-run hardening branch upgrades Go to 1.26.5, removes reachable Go
vulnerabilities, repairs the public CI route, and adds browser/accessibility
gates. These changes passed the commit-bound CI run identified above.
Current-source Temporal Replay v2 now also passes in two distinct
operating-system environments. Authorized domain-expert review remains required
before making business-policy correctness claims in an article.
