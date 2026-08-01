
# Frozen evidence baseline

The pre-hardening source state is frozen independently from later evidence-hardening edits.

| Repository | Commit | Branch | Tag | Initial status |
|---|---|---|---|---|
| engine-rms / differential package | d6004755fa6dd0c8d6be01f84b851f0b50d8a12f | main | tpr-ir-differential-fixed-v1 | clean |
| papa-website-v2 | 4f2e402b07811ae90f846cdcc3c7d9f6df5bd411 | main | tpr-ir-differential-fixed-v1 | clean |

| Runtime | Observed value |
|---|---|
| php | PHP 8.4.20 (cli) (built: Apr  8 2026 08:28:30) (ZTS Visual C++ 2022 x64) |
| laravel | Laravel Framework 10.50.2 |
| phpunit | PHPUnit 10.5.64 by Sebastian Bergmann and contributors. |
| mysql | 8.0.30 |
| mysql_collation | utf8mb4_0900_ai_ci |
| go | go version go1.26.2 windows/amd64 |
| grule | require github.com/hyperjumptech/grule-rule-engine v1.20.4 |
| operating_system | Windows-10-10.0.19045-SP0 |
| timezone | Asia/Bangkok |
| locale | en-US |
| docker | NOT_AVAILABLE |
| docker_compose | NOT_AVAILABLE |

Structured source: `FROZEN_EVIDENCE_BASELINE.json`. The final fixed source is separately bound in `runs/fixed/source-state.json`; this document does not rewrite the historical freeze after hardening changes.

Evidence-hardening source/test tag: `tpr-ir-evidence-hardening-v2` at engine/package commit `3e2746846da850d0d6ad213c892086c160835c39` and Laravel test commit `a6f4f102efd93057a98438e2a68dffaa3425d954`.
