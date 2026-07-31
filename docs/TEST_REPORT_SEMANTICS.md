# Test Report - TPR-IR Semantics

Tanggal eksekusi: 2026-08-01.

## Hasil berhasil

| Suite | Hasil |
|---|---|
| `go test ./... -count=1` | PASS, package `rule-engine`, 5.185s pada run final; termasuk bootstrap kontrak Laravel |
| `go vet ./...` | PASS |
| Go statement coverage | PASS, 86.6% pada pengukuran terakhir |
| Laravel `TypedPayrollRuleIrServiceTest` + `RuleDefinitionSemanticContractTest` | PASS, 6 tests, 21 assertions |
| Laravel payroll regression (`PayrollRuleEngineWhiteBoxUnitTest`, `PayrollRuleEngineTaxableComputationUnitTest`, `PayrollRuleEngineTaxableComputationTest`, `SalaryRuleEnginePersistenceTest`) | PASS, 24 tests, 140 assertions, 15.33s |
| Laravel facts + real-engine matrix (`PayrollBuildFactsAttendanceSourceUnitTest`, `PayrollRuleEngineFormulaMatrixIntegrationTest`, `PayrollRuleEngineRealIntegrationTest`) | PASS, 30 tests, 131 assertions, 25.07s |
| Seluruh suite semantic/payroll di atas dalam satu proses | PASS, 60 tests, 292 assertions, 41.78s |
| PHP syntax lint untuk file yang diubah | PASS |
| JSON parse `TPR_IR_SCHEMA.json` | PASS |

Jumlah Go test function saat laporan: 64, termasuk test TPR/cross-language serta test legacy/branch terdahulu.

## Oracle semantik

- Schema: valid, missing/unsupported version, unknown namespace/field, wrong literal type.
- HTTP trust boundary: POST-only, 1 MiB body, unknown property, trailing JSON.
- Condition: AND, OR, nested group, empty group, missing fact, membership, numeric boundary, Unicode Contains, maximum leaf.
- Formula: valid AST, unknown identifier, invalid token, raw-GRL/function injection, zero division, max depth, numeric overflow, unary minus.
- Money: 0.1+0.2, 1/3, positive/negative HALF_UP ties, dan nilai besar.
- Conflict: ADD+ADD COLLECT_SUM, SET+ADD reject, SET+SET PRIORITY, FIRST, PRIORITY tie, UNIQUE potential conflict.
- Determinism: rule permutation, canonical hash, JSON round-trip, identical GRL/output, stable source ID.
- Cross-language: Laravel normalizer aktual divalidasi dan dieksekusi Go; real HTTP integration suite juga lulus.

## Metamorphic relations

| Relasi | Hasil |
|---|---|
| Tambah always-false rule | PASS, output tidak berubah |
| Tukar rule independen | PASS, semantic output/hash tidak berubah |
| Serialize-deserialize IR | PASS, GRL/output stabil |
| Formula ekuivalen `1+2` dan `3` | PASS |
| Split ADD 40+60 versus total 100 | PASS |
| Naikkan positive rate | PASS, hasil tidak turun |
| Ubah description | PASS, semantic hash tidak berubah |
| Input/IR/policy sama | PASS pada repeated execution dan identical GRL |

Tidak ditemukan counterexample pada relasi yang dijalankan. Counterexample baseline yang diperbaiki adalah ketergantungan legacy `source_rule` dan SET/ADD pada urutan rule. Stable provenance dan policy resolver kini memutus ketergantungan hasil bisnis tersebut; index legacy dipertahankan hanya untuk kompatibilitas.

## Regression database setelah MySQL aktif

MySQL testing `website_papa_v2_testing` sudah dapat diakses. Retry awal menemukan dan memperbaiki masalah berikut:

1. Payload normal dibangun sebelum default eksplisit `rates.tax_flat_amount=0`, sehingga formula tax aktif ditolak sebagai unknown identifier. Default kini dipasang sebelum katalog TPR-IR dibangun.
2. Fixture `SalaryRuleEnginePersistenceTest` tidak memiliki `project_team`, memakai aktor yang tidak berwenang, tidak membekukan tanggal, dan tidak menyediakan jadwal kerja. Fixture kini deterministik serta mengikuti RBAC/jadwal aktual.
3. Fixture integrasi lama belum membawa `has_npwp`, `ptkp_status`, pasangan menit/jam konsisten, dan masih menguji condition `active` padahal kontrak permanent dinormalisasi menjadi status canonical `tetap`.
4. Fallback komponen `OVERTIME_PAY` hanya memakai rate per menit. Jalur rate per jam kini dihitung eksplisit bila rate per menit tidak tersedia.

Seluruh 54 test database-backed payroll/TPR yang dipilih lulus dengan 271 assertions.

Full Laravel run sebelum pembaruan fixture mencatat 119 pass dan 36 fail. Seluruh failure kemudian diperbaiki, termasuk fixture PM, kontrak redirect web, variabel view director, teks workflow pajak, dan cache schema model yang sebelumnya bocor antar-test. Full run final lulus 155 tests dan 835 assertions dalam 114.81s.

Gobco current condition coverage dihentikan oleh timeout 300 detik tanpa output final. Angka lama 98.94% tidak digunakan sebagai hasil TPR karena denominator source telah berubah.

## Unresolved validation evidence

1. Race run tetap memerlukan CGO/C compiler pada environment Windows ini.
2. Rollout audit tetap perlu memastikan active data tidak mempunyai konflik yang kini ilegal.

## Kesimpulan readiness

Semantik typed IR, conflict policy, priority/salience, formula safety, database-backed payroll regression, real Laravel-to-Go integration, dan full Laravel suite sudah lulus. Baseline siap memasuki differential oracle validation setelah commit/tag dan preflight data audit diselesaikan.
