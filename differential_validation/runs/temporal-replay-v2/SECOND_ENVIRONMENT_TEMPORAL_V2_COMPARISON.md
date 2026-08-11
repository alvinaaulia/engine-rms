# Temporal Replay v2 Second-Environment Comparison

Status: `SECOND_ENVIRONMENT_PASS`

## Runs

- Primary Windows: `temporal-v2-20260802T184637Z-70ea55a6`
- Secondary WSL 2 native, no Docker: `temporal-v2-20260811T085034Z-9e6b3f3c`
- Engine commit: `0dc6c0032484285fce37001b80323cd4c1afd86c`
- Laravel commit: `45b82783056a4277f32517667ab519a104550e7c`

## Cross-environment result

- Both manifests: `PASS`; all gates passed in both environments.
- Cases: 418 in each environment.
- Supported attempts: 824/824 matched in each environment.
- Expected rejections: 12/12 accepted in each environment.
- Component amount: 1600/1600 in each environment.
- Summary fields: 3296/3296 in each environment.
- Provenance fields: 7416/7416 in each environment.
- Per-case comparator payloads: 418/418 byte-equivalent canonical payload hashes; mismatches: 0.
- Payload integrity: 30,536/30,536 envelopes passed independently in each environment.
- Legacy signature: reconstructed baseline 8 mismatches twice; fixed 0 mismatches in both environments.

## Environment distinction

- Primary: `Windows-10-10.0.19045-SP0`; PHP `8.4.20`; Go `go version go1.26.2 windows/amd64`.
- Secondary: `Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43`; PHP `8.5.4`; Go `go version go1.25.6 linux/amd64`.

## Scope

This closes the second-environment technical reproduction gate for Temporal Replay v2. It does not convert the technical reference oracle into an authoritative payroll-policy oracle. Domain status remains `NOT_AUTHORITATIVE_BUSINESS_ORACLE / DOMAIN_VALIDATION_PENDING`.
