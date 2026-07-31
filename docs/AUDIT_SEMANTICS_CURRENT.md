# Audit Semantik Aktual Payroll Rules

Tanggal audit: 2026-08-01. Baseline ini dibekukan sebelum perubahan production TPR-IR. Sumber yang diaudit adalah `RuleDefinitionValidator`, `RuleController`, `PayrollRuleEngineService`, model rule Laravel, serta `model.go`, `rule_executor.go`, `emitter.go`, `calculator.go`, dan `decimal.go` pada engine Go.

## Peta representasi aktual

| Elemen | Representasi Laravel | Representasi JSON | Representasi Go | Representasi GRL | Status semantik |
|---|---|---|---|---|---|
| Rule master | `rules`, mempunyai banyak version | Tidak dikirim langsung | Tidak ada tipe master | Tidak ada | implisit |
| Rule version | `RuleVersion`, status, approval, version, definition | ID disisipkan ke `meta` | Sebelumnya tidak dimodelkan | Nama `Rule_<index>` | tidak konsisten |
| Condition tree | list implisit AND atau object `{type,rules}` | object/list bebas tanpa discriminator | `interface{}` | ekspresi rekursif dengan kurung | ambigu |
| Condition leaf | field/operator/value | nilai tidak mempunyai type tag | map bebas saat translator | perbandingan literal | tidak aman |
| Empty group | Laravel menolak | dapat dikirim langsung ke Go | sebelumnya menjadi ekspresi kosong | rule dilewati | tidak konsisten |
| Depth | Controller membatasi 2 group | tidak ada deklarasi schema | tidak dibatasi | rekursif | tidak aman |
| Leaf count | validator membatasi 50 | tidak dideklarasikan | tidak dibatasi | seluruh leaf diterjemahkan | tidak konsisten |
| Field employee | registry statis bertipe | string path | alias statis dan dynamic `Text` fallback | property/method | sebagian eksplisit |
| Field attendance | registry statis numeric | string path | alias dan dynamic `Value` | property/method | sebagian eksplisit |
| Rate | key aktif dari database | `rates.<key>` | dynamic `Value` menerima key payload | method call | implisit |
| Component reference | component aktif, uppercase | `components.<CODE>` | dynamic `Value` | method call | sebagian eksplisit |
| Unknown field | Laravel menolak | masih dapat menghindari Laravel | `normalizeField` mengembalikan input mentah | raw fragment dapat masuk GRL | tidak aman |
| Numeric literal | `is_numeric`, termasuk string | number/string | coercion dinamis | literal bebas | tidak konsisten |
| Boolean literal | boolean ketat di Laravel | boolean | parser lama menerima string/numeric | bool literal | tidak konsisten |
| Date literal | `Carbon::parse` permisif | string bebas | dibanding sebagai string | lexical compare | tidak konsisten |
| String equality | case-sensitive | scalar | literal string | `==` | implisit |
| CONTAINS | diizinkan untuk string | operator string | helper lower-case | `helper.Contains` | implisit |
| IN/NOT_IN | list non-kosong | array | empty list menghasilkan false/true | rangkaian OR/AND | tidak konsisten |
| Action | tepat satu `action` | `{type,code,formula}` | satu `Action` | satu method call | eksplisit secara bentuk |
| ADD_COMPONENT | append component | string action | `Emitter.AddComponent` | `out.ApplyComponent` | ambigu untuk target sama |
| SET_COMPONENT | replace first component dengan code sama | string action | `Emitter.SetComponent` | `out.ApplyComponent` | bergantung urutan |
| Formula | tokenizer Laravel | raw string | regex replacement | raw arithmetic fragment | tidak aman |
| Formula dependency | registry Laravel | identifier path | dynamic method fallback | property/method | sebagian eksplisit |
| Priority | HIGH/NORMAL/LOW | `meta.priority` | sebelumnya diabaikan | tanpa salience | tidak konsisten |
| Ordering | priority rank lalu ID DB | urutan array | urutan array | agenda GRULE | implisit |
| Multiple match | tidak dianalisis formal | tidak ada policy | seluruh rule dapat emit | agenda engine | ambigu |
| Conflict target sama | tidak dianalisis | tidak ada policy | efek SET/ADD order-dependent | firing order | tidak aman |
| Retract | tidak dikenal Laravel | tidak ada | selalu dihasilkan | rule retract setelah action | eksplisit |
| MaxCycle | tidak dikirim | tidak ada | default engine | engine default | tidak aman |
| Effective period | meta + status DB | meta tanggal | tidak dievaluasi Go | tidak ada | trust pada Laravel |
| Component provenance | source map index/ID/action code | `source_rule` integer | index array | literal index | tidak konsisten |
| Summary | BigDecimal Laravel melakukan normalisasi ulang | amount float | decimal rational scale 6 | hasil formula float | sebagian eksplisit |
| Rounding | beberapa helper `HALF_UP` | decimal string/number | rational lalu HALF_UP scale 6 | evaluasi binary sebelum boundary | sebagian eksplisit |

## Temuan risiko

1. Fallback field mentah membuat trust boundary Go tidak independen dan dapat membentuk GRL yang tidak berasal dari allowlist.
2. Priority hanya memengaruhi urutan array Laravel; tidak mempunyai arti agenda GRULE.
3. SET dan ADD pada target sama mempunyai hasil yang bergantung firing order.
4. `source_rule` berbasis index berubah saat urutan payload berubah.
5. Formula lama tidak memiliki AST dan raw string menjadi fragmen GRL setelah regex replacement.
6. Laravel dan Go berbeda untuk coercion boolean, tanggal, empty membership, unknown field, depth, dan jumlah leaf.
7. Request body, jumlah rule/action, formula depth, deadline, dan cycle tidak dibatasi secara lengkap.
8. Dynamic getter lama mengubah missing atau invalid numeric menjadi nol; konfigurasi salah dapat tampak sebagai hasil bisnis yang sah.

## Baseline keputusan

Perilaku yang dipertahankan melalui adapter: satu legacy action per rule, decimal-string facts, priority default NORMAL, component/rate dynamic yang benar-benar terdapat pada facts, dan response `source_rule`. Perilaku yang tidak dijadikan spesifikasi: raw-field fallback, default ADD untuk action asing, empty group sebagai false, tie berdasarkan ID database, serta last/first writer yang muncul dari firing order.
