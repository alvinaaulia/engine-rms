# Code Change Report — TPR-IR 1.0

Tanggal: 2026-08-01.

## Go engine-rms

| File | Perubahan |
|---|---|
| `model.go` | Metadata legacy, typed ruleset request, dan stable/multi-source component provenance |
| `tpr_ir.go` | DTO TPR-IR, priority mapping, legacy adapter, canonical validator/hash, catalog, limits, conflict analyzer |
| `formula_parser.go` | Lexer, recursive-descent AST parser, constant-zero/overflow/depth checks, safe GRL emitter |
| `tpr_executor.go` | Salience translator, context deadline, MaxCycle, candidate collector, formal hit-policy resolver |
| `rule_executor.go` | Seluruh legacy execution dirutekan ke adapter TPR; raw-field fallback dihapus |
| `main.go` | Strict JSON boundary, body/method/deadline limits, schema dispatch, structured validation error, server timeout |
| `tpr_ir_test.go` | Schema, condition, formula, conflict, determinism, metamorphic, HTTP, dan real Laravel→Go contract tests |

`emitter.go` dipertahankan untuk API/test legacy, tetapi production execution baru memakai `CandidateCollector`. Legacy translator helper tetap tersedia untuk test dokumentasi; entry point `/execute` dan `executeAllRules*` selalu melewati canonical TPR.

## Laravel papa-website-v2

| File | Perubahan |
|---|---|
| `app/Services/TypedPayrollRuleIrService.php` | Normalizer/adapter DTO Laravel → TPR-IR v1, priority/hit policy/catalog/canonical ordering |
| `app/Services/RuleConflictAnalyzer.php` | Pre-runtime duplicate, mixed SET/ADD, overlapping-period SET priority-tie analysis |
| `app/Services/PayrollRuleEngineService.php` | Payload normal dan pre-tax mengirim envelope/ruleset TPR; default tax nol tersedia sebelum katalog; fallback overtime per jam eksplisit |
| `app/Services/RuleDefinitionValidator.php` | Canonical YYYY-MM-DD dan pemisahan eksplisit kontrak operator numeric/date |
| `app/Http/Controllers/Rules/RuleController.php` | Conflict check sebelum submit, approval, activation; replacement version master yang sama dikecualikan |
| `tests/Unit/TypedPayrollRuleIrServiceTest.php` | Contract, illegal field/formula, conflict, priority, rounding, permutation |
| `tests/Unit/RuleDefinitionSemanticContractTest.php` | Canonical date dan operator-type contract |
| `tests/Feature/SalaryRuleEnginePersistenceTest.php` | Fixture MySQL/RBAC/jadwal dibuat deterministik sesuai kontrak runtime |
| `tests/Unit/PayrollBuildFactsAttendanceSourceUnitTest.php` | Jadwal kerja eksplisit dan presisi performance score |
| `tests/Feature/PayrollRuleEngineFormulaMatrixIntegrationTest.php` | Facts pajak/periode lengkap, status canonical, dan sinkronisasi minute-hour |
| `tests/Feature/PayrollRuleEngineRealIntegrationTest.php` | Facts lengkap dan rule condition memakai status canonical `tetap` |

## Compatibility dan migration

- Payload lama tidak dihapus. Go mengenal payload tanpa `ruleset`, memvalidasi lalu mengadaptasikannya.
- Legacy numeric/boolean condition value hanya boleh dicoerce di adapter; typed literal v1 tetap strict.
- Legacy decimal-string facts menjadi representasi wire resmi untuk numeric facts.
- Action legacy satu-per-rule menjadi array satu action.
- Priority kosong menjadi NORMAL=50.
- Legacy ADD-only target menjadi COLLECT_SUM; SET-only menjadi PRIORITY; campuran ditolak.
- Response `source_rule` tetap ada. Consumer baru memakai stable ID/version ID dan contributor arrays.
- Tidak ada migration database pada tahap ini. Policy masih diinferensi; penyimpanan policy eksplisit menunggu keputusan bisnis.

## Known limitations

1. UI/database belum mempunyai editor/persistence hit policy; normalizer menginferensinya.
2. UNIQUE validation konservatif dan belum membuktikan mutual exclusivity condition.
3. Nullable, NOT, datetime, formula function, dan dependency graph antar-output tidak didukung v1.
4. GRULE menghitung expression menggunakan numeric runtime engine; decimal rational diterapkan pada monetary boundaries, bukan setiap node AST.
5. Hit policy masih diinferensi dan belum disimpan sebagai keputusan eksplisit pada database/UI.
6. Legacy `source_rule` index tetap order-sensitive; stable provenance baru tidak order-sensitive.

## Migration checklist

1. Audit active rules untuk target SET yang priority-nya tie serta target campuran SET/ADD.
2. Pastikan semua tanggal tersimpan sebagai YYYY-MM-DD.
3. Ubah consumer provenance ke `source_rule_version_id`/`source_rule_ids`.
4. Tambahkan kolom/UI hit policy sebelum mengizinkan policy selain inferensi default.
5. Jalankan differential validation terhadap oracle independen sebelum temporal replay atau rollout aplikasi penuh.
