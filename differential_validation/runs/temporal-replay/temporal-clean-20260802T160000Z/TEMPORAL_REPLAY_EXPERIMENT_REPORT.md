# Temporal Replay Experiment Report

## Executive verdict

The local clean temporal experiment passed all executable gates. Domain validation remains pending and the synthetic oracle is not an authoritative business oracle.

## Dataset and execution

- Synthetic profiles: 30
- Payroll periods: 12
- Matrix originals: 360
- Targeted cases: 48
- Total cases: 408
- Repeats: 2
- Supported replay attempts: 808
- Expected rejection attempts: 8

## Exactness and integrity

- Supported exact matches: 808/808 (100%)
- Expected artifact rejections: 8/8
- Manifest completeness: 100%
- Current-state contamination violations: 0
- Live salary side-effect violations: 0
- Mutation-wave gate: PASS

## Performance observation

Replay latency in microseconds: p50=57169, p95=126401, p99=197119, min=34441, max=1370512.
The serialized manifest JSONL artifact occupies 3373351 bytes. These values describe this recorded local environment; they are not a general production benchmark.

## Regression

- Reconstructed baseline repeat 1: 624 cases, 8 mismatches
- Reconstructed baseline repeat 2: 624 cases, 8 mismatches
- Fixed implementation: 624 cases, 0 mismatches
- Laravel: 164 tests, 1615 assertions, 0 failures, 0 errors, 0 skipped
- Go tests and go vet: PASS (exit-code evidence in raw-logs)

## Domain limitation

`NOT_AUTHORITATIVE_BUSINESS_ORACLE / DOMAIN_VALIDATION_PENDING`. This run supports implementation correctness and temporal isolation claims only.
