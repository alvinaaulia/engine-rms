# Typed Payroll Rule Intermediate Representation (TPR-IR) 1.0

## Kontrak umum

TPR-IR adalah representasi canonical antara authoring Laravel dan executor Go. Envelope eksekusi mempunyai `schema_version`, `ruleset`, `facts`, dan `component_types`. Semua object schema memakai `additionalProperties: false`; discriminator `kind` membedakan group dan leaf. Unknown field, namespace, operator, action, formula reference, dan schema version ditolak sebelum GRULE dibangun.

Alur migrasi: legacy payload → validasi adapter → normalisasi TPR-IR 1.0 → canonical validation → AST formula → GRL → candidate resolution.

## Tipe

- `RuleSet`: version, identity, default/per-component hit policy, rounding, effective period, field catalog, rules.
- `Rule`: stable ID, optional version ID, numeric priority, metadata non-eksekusi, effective period, condition, 1–8 actions.
- `ConditionNode`: `kind=group` dengan AND/OR dan children, atau `kind=leaf` dengan typed field/literal.
- `FieldReference`: namespace, name, data type, nullable, dan operator yang diikat oleh catalog.
- `RateReference`: bentuk semantik `rates.<key>`; key harus ada pada field catalog dan facts.
- `ComponentReference`: target action `{code}` atau formula field `components.<CODE>`.
- `TypedLiteral`: `{type,value}`; membership memakai `array<T>` non-kosong.
- `FormulaExpression`: language wajib `TPR-EXPR-1.0` dan source expression.
- `ValidationError`: stable `error_code`, JSON path, message, optional details.

Namespace v1.0 hanya `employee`, `attendance`, `rates`, dan `components`. Namespace `tax` dan `contract` belum menjadi namespace facts terpisah; nilai kontrak/tax yang tersedia tetap direpresentasikan sebagai field employee/rates yang terdaftar. Field asing tidak memiliki fallback.

## Operator

| Tipe Data | Operator | Null Behavior | Invalid Input Behavior | GRL Mapping |
|---|---|---|---|---|
| numeric | EQ, NEQ, GT, GTE, LT, LTE | nullable tidak didukung v1 | reject | `== != > >= < <=` |
| numeric | IN, NOT_IN | nullable tidak didukung | reject type/empty array | OR equality / AND inequality |
| string | EQ, NEQ | nullable tidak didukung | reject | `== !=` case-sensitive |
| string | CONTAINS | nullable tidak didukung | reject | helper Unicode case-insensitive |
| string | IN, NOT_IN | nullable tidak didukung | reject type/empty array | OR/AND, equality case-sensitive |
| boolean | EQ, NEQ | nullable tidak didukung | reject non-boolean literal | `== !=` |
| date | EQ, NEQ, BEFORE, AFTER, ON_OR_BEFORE, ON_OR_AFTER | nullable tidak didukung | reject selain YYYY-MM-DD | lexical ISO comparison |
| date | IN, NOT_IN | nullable tidak didukung | reject type/empty array | OR/AND ISO equality |

Canonical literal tidak melakukan silent coercion. Compatibility adapter boleh mengubah numeric/boolean legacy yang dikenal, lalu menghasilkan literal canonical bertipe. Numeric payroll facts memakai canonical decimal string secara eksplisit untuk mencegah hilangnya presisi melalui binary JSON float. Missing required fact dan type mismatch adalah validation error.

Date adalah tanggal kalender bisnis tanpa time-of-day atau timezone. Format tunggal `YYYY-MM-DD`; datetime dan NOT tidak didukung v1.0.

## Condition tree

AND/OR selalu diberi kurung pada GRL sehingga precedence tidak bergantung parser. Group kosong ditolak. Minimal satu leaf, maksimal 50 leaf per rule. Maksimal dua tingkat group. Evaluasi GRULE dapat short-circuit sesuai AND/OR, tetapi tidak boleh mengubah hasil murni karena leaf tidak mempunyai side effect. Canonicalization menyortir children AND/OR berdasarkan JSON canonical karena kedua operator komutatif untuk leaf murni.

## Priority, actions, dan hit policy

Mapping: HIGH=100, NORMAL=50, LOW=10. Nilai TPR 0–1000 valid; translator selalu menulis `salience <priority>` pada setiap rule GRULE. Canonical order adalah priority descending lalu stable rule ID ascending.

Satu rule v1.0 dapat memiliki 1–8 actions. Laravel legacy saat ini menghasilkan satu action. Action hanya `SET_COMPONENT` atau `ADD_COMPONENT`.

| Action A | Action B | Hit Policy | Expected Result |
|---|---|---|---|
| SET | SET | UNIQUE | lebih dari satu potential producer ditolak |
| SET | SET | FIRST | stable first: priority desc, rule ID asc |
| SET | SET | PRIORITY | priority tertinggi; potential/matching tie ditolak |
| ADD | ADD | COLLECT_SUM | seluruh match dijumlahkan, HALF_UP di boundary |
| SET | ADD | semua | ditolak sebelum runtime |
| ADD | SET | semua | ditolak sebelum runtime |
| ADD | ADD | FIRST/PRIORITY/UNIQUE | resolver policy biasa, tetapi harus dinyatakan eksplisit |
| duplicate rule/action | semua | semua | duplicate ID/rule ditolak |

`UNIQUE` memakai conservative validation: lebih dari satu potential producer target ditolak, sehingga tidak diperlukan satisfiability proof. `FIRST` tidak memakai array/DB order. `PRIORITY` tie tidak memakai ID sebagai pemenang; tie adalah error. `COLLECT_SUM` hanya menerima ADD.

Adapter legacy memilih COLLECT_SUM bila seluruh action target adalah ADD, PRIORITY bila seluruhnya SET, dan menolak campuran. Missing priority menjadi NORMAL=50.

## Formula dan uang

Grammar:

```text
expression := term (("+" | "-") term)*
term       := unary (("*" | "/") unary)*
unary      := ("+" | "-") unary | primary
primary    := numeric_literal | numeric_field_reference | "(" expression ")"
```

Function call, string, comma, statement separator, assignment, raw GRL, identifier asing, NaN, infinity, overflow literal, constant zero divisor, lebih dari 1000 karakter, dan depth di atas 32 ditolak. Parser menghasilkan AST; emitter GRL hanya menerima node AST dan safe field mapping. Dynamic zero divisor atau non-finite runtime result menghasilkan error, bukan component nol diam-diam.

Money memakai decimal rational pada boundary, scale 6, HALF_UP (ties away from zero), termasuk nilai negatif. Rounding dilakukan saat candidate diterima, setelah COLLECT_SUM, dan saat summary boundary. PHP memakai BigDecimal dengan kebijakan sama. JSON facts numeric dapat berupa canonical decimal string; output API tetap number untuk kompatibilitas.

## Canonical serialization dan provenance

JSON key dihasilkan oleh struct/DTO tetap; field catalog dan rules diurutkan; children komutatif diurutkan. Semantic SHA-256 tidak memasukkan legacy index atau description. Stable identity memakai `rule-version-<id>` atau hash canonical legacy. Response menambah `source_rule_id`, `source_rule_version_id`, dan daftar contributor untuk COLLECT_SUM, serta mempertahankan `source_rule` index untuk client lama.

## Batas trust boundary Go

Body 1 MiB; maksimal 500 rules; depth 2; 50 leaves/rule; 8 actions/rule; formula 1000 karakter/depth 32; schema 1.0; HTTP POST; deadline 5 detik; GRULE MaxCycle `rules × 8 + 1`; JSON unknown properties ditolak oleh decoder typed. Client menerima error terstruktur tanpa stack trace atau generated GRL.

## Contoh valid ringkas

```json
{"schema_version":"1.0","ruleset":{"schema_version":"1.0","ruleset_id":"payroll-2026-08","default_hit_policy":"COLLECT_SUM","rounding_policy":{"scale":6,"mode":"HALF_UP"},"field_catalog":[{"reference":{"namespace":"employee","name":"status","data_type":"string","nullable":false},"allowed_operators":["EQ","NEQ","CONTAINS","IN","NOT_IN"]}],"rules":[{"id":"rule-version-42","version_id":42,"priority":100,"metadata":{},"condition":{"kind":"leaf","operator":"EQ","field":{"namespace":"employee","name":"status","data_type":"string","nullable":false},"literal":{"type":"string","value":"aktif"}},"actions":[{"type":"ADD_COMPONENT","target":{"code":"BONUS"},"formula":{"language":"TPR-EXPR-1.0","expression":"1000"}}]}]},"facts":{"employee":{"status":"aktif"},"attendance":{},"rates":{},"components":{}},"component_types":{"BONUS":"EARNING"}}
```

Invalid: `employee.password`, numeric literal `"10"` dalam canonical condition, empty IN, SET+ADD target sama, PRIORITY tie, `1; Retract("x")`, `1/0`, atau schema `2.0`.
