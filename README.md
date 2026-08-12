# RMS Typed Payroll Rule Engine

Go/GRULE execution service and reproducible validation package for the typed
payroll-rule IR and temporal replay study.

## Local service

Requirements: Go 1.25.6 or newer. The service listens only on
`127.0.0.1:8081` by default.

```bash
export RULE_ENGINE_INTERNAL_TOKEN='replace-with-a-long-random-secret'
go run .
```

Configure the Laravel application with the same `RULE_ENGINE_INTERNAL_TOKEN`.
Set `RULE_ENGINE_ADDR` only when a different bind address is required. A
non-loopback deployment must use a token and a protected network segment.

## Verification

Fast unit/security gate:

```bash
go test -short ./... -count=1 -timeout=3m
go vet ./...
```

Cross-language integration gate (requires the Laravel repository as sibling
`../papa-website-v2` and PHP dependencies installed):

```bash
go test ./... -count=1 -timeout=10m
```

Robustness/performance smoke gates:

```bash
go test -run '^$' -fuzz '^FuzzExecuteHTTPTrustBoundary$' -fuzztime=10s -timeout=45s
go test -run '^$' -bench '^BenchmarkRuleEngineScale$' -benchtime=1x -benchmem -timeout=3m
```

The benchmark covers 1, 10, and 50 rules. Higher scales require a dedicated
performance protocol and are not part of the supported scalability claim.

Research artifacts, schemas, raw run manifests, and their validation scripts
are under `differential_validation/`. Domain decisions intentionally remain
pending until completed by an authorized payroll/tax reviewer.

## Research claim boundary

The evidence supports deterministic translation/execution and replay for the
frozen synthetic corpus. It does not by itself establish legal payroll or tax
correctness for every organization or jurisdiction.

## Data availability

The Go source and synthetic evidence are stored in this repository. The paired
Laravel source may be restricted by company confidentiality. A submission must
either provide a sanitized reviewer package pinned to an exact commit or state
the restriction and access procedure in its Data Availability Statement.
