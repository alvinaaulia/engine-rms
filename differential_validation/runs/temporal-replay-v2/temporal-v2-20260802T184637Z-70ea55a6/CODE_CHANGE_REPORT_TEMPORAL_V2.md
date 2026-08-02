# Code Change Report — Temporal Replay v2

## Engine and validation package
```
differential_validation/Makefile                   |   5 +-
 .../TEMPORAL_REPLAY_V2_SOURCE_BASELINE.md          |  22 +
 .../TEMPORAL_V1_CLAIM_MATRIX.csv                   |  21 +
 .../TEMPORAL_V1_EVIDENCE_AUDIT.md                  |  39 ++
 .../capture_temporal_v2_environment.py             |  75 +++
 differential_validation/finalize_temporal_v2.py    | 667 +++++++++++++++++++++
 .../scripts/clean_temporal_v2.sh                   | 125 ++++
 .../artifact-envelope.schema.json                  |  48 ++
 .../artifact-hashes.schema.json                    |  11 +
 .../comparator-result.schema.json                  |  35 ++
 .../correlation-event.schema.json                  |  19 +
 .../exactness-metrics.schema.json                  |  32 +
 .../forbidden-lookup-trace.schema.json             |  18 +
 .../mutation-wave.schema.json                      |  29 +
 .../original-output.schema.json                    |  12 +
 .../replay-request.schema.json                     |  26 +
 .../replay-response.schema.json                    |  26 +
 .../replay-result.schema.json                      |  34 ++
 .../side-effect-result.schema.json                 |  17 +
 .../temporal-case-index.schema.json                |  14 +
 .../temporal-manifest.schema.json                  |  28 +
 .../time-provenance.schema.json                    |   8 +
 .../version-applicability.schema.json              |  16 +
 .../verify_temporal_v2_payload_hashes.php          |  85 +++
 replay.go                                          | 133 +++-
 replay_test.go                                     |  72 +++
 tpr_executor.go                                    |   3 +
 tpr_ir.go                                          |  13 +-
 28 files changed, 1613 insertions(+), 20 deletions(-)
```

## Laravel
```
.../RunTemporalReplayEvidenceClosureV2.php         | 1044 ++++++++++++++++++++
 .../Commands/RunTemporalReplayExperiment.php       |   23 +-
 app/Models/Payroll/PayrollReplayRun.php            |    4 +-
 app/Services/TemporalReplay/CanonicalJson.php      |   21 +-
 .../TemporalReplay/CurrentStateLookupGuard.php     |   24 +-
 app/Services/TemporalReplay/ReplayComparator.php   |   45 +-
 .../TemporalPayrollReplayService.php               |  124 ++-
 .../VersionApplicabilityEvaluator.php              |   59 ++
 ...002_add_temporal_replay_v2_evidence_columns.php |   46 +
 .../TemporalPayrollReplayPersistenceTest.php       |   22 +-
 tests/Unit/TemporalPayrollReplayUnitTest.php       |   38 +
 11 files changed, 1427 insertions(+), 23 deletions(-)
```

The v1 evidence directories remain retained. Frozen expected outputs were not modified.
