
# Automated evidence generation report

| Command | Evidence file | Parser | Exit | Started | Finished | Seconds | Status |
|---|---|---|---|---|---|---|---|
| laravel | laravel-tests.xml | 2.0 | 0 | 2026-08-01T04:47:07.610338+00:00 | 2026-08-01T04:49:23.105149+00:00 | 135.494856 | PASS |
| go | go-tests.stdout.log | 2.0 | 0 | 2026-08-01T04:46:25.751924+00:00 | 2026-08-01T04:46:41.612010+00:00 | 15.860126 | PASS |
| go_vet | go-vet.stdout.log | 2.0 | 0 | 2026-08-01T04:46:42.577343+00:00 | 2026-08-01T04:46:49.478518+00:00 | 6.901224 | PASS |
| translator | translator-go-test.stdout.log | 2.0 | 0 | 2026-08-01T04:46:11.774054+00:00 | 2026-08-01T04:46:25.014808+00:00 | 13.240828 | PASS |
| e2e | e2e-junit.xml | 2.0 | 0 | 2026-08-01T04:45:26.460650+00:00 | 2026-08-01T04:45:44.045238+00:00 | 17.584631 | PASS |
| corpus | corpus-generation.stdout.log | 2.0 | 0 | 2026-08-01T04:51:07.382883+00:00 | 2026-08-01T04:51:08.246238+00:00 | 0.863396 | PASS |
| oracle | oracle-generation.stdout.log | 2.0 | 0 | 2026-08-01T04:51:08.988191+00:00 | 2026-08-01T04:51:10.010338+00:00 | 1.022195 | PASS |
| oracle_verifier | oracle-verification.stdout.log | 2.0 | 0 | 2026-08-01T04:51:10.856697+00:00 | 2026-08-01T04:51:11.731079+00:00 | 0.874425 | PASS |
| baseline_differential | differential.stdout.log | 2.0 | 0 | 2026-08-01T04:51:49.695467+00:00 | 2026-08-01T04:52:09.061459+00:00 | 19.366035 | PASS |
| fixed_differential | differential.stdout.log | 2.0 | 0 | 2026-08-01T04:51:19.080229+00:00 | 2026-08-01T04:51:37.526120+00:00 | 18.445933 | PASS |

The generator refuses missing, malformed, failed, inconsistent, or stale evidence. Its parser tests cover those conditions and the absence of a hard-coded fallback. Test/assertion counts and durations below are parsed from JUnit or Go JSON events.

| Suite | Tests | Passed | Failed | Skipped | Assertions | Seconds |
|---|---|---|---|---|---|---|
| Laravel full suite | 157 | 157 | 0 | 0 | 1519 | 130.900633 |
| Go full suite | 204 | 204 | 0 | 0 | not emitted | 6.529 |
| Translator fixture test | 13 | 13 | 0 | 0 | not emitted | 4.4719999999999995 |
| Full-pipeline E2E PHPUnit | 1 | 1 | 0 | 0 | 682 | 14.385423 |
