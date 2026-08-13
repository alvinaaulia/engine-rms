# Temporal Replay v2 Second-Environment Comparison

Status: `SECOND_ENVIRONMENT_PASS`

## Runs

- Primary Windows: `temporal-v2-20260813T195025Z-9379cd45`
- Secondary WSL 2 native, no Docker: `temporal-v2-20260813T211003Z-a7304d0d`
- Engine commit: `0f756cecb16a6271f24c3de239319a684807eaf5`
- Laravel commit: `aa6b05f9d62cc277decc59cc44745ada5e56ccae`

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

- Primary: `Windows-10-10.0.19045-SP0`; PHP `8.4.20`; Go `go version go1.26.5 windows/amd64`.
- Secondary: `Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.43`; PHP `8.5.4`; Go `go version go1.26.5 linux/amd64`.

## Scope

This closes the second-environment technical reproduction gate for Temporal Replay v2. It does not convert the technical reference oracle into an authoritative payroll-policy oracle. Domain status remains `NOT_AUTHORITATIVE_BUSINESS_ORACLE / DOMAIN_VALIDATION_PENDING`.
