# Semantic Decision Log

| ID | Keputusan | Alasan | Dampak kompatibilitas |
|---|---|---|---|
| SDL-001 | Schema TPR-IR dibekukan pada `1.0` | Evolusi kontrak harus eksplisit | payload tanpa ruleset tetap melalui adapter |
| SDL-002 | HIGH=100, NORMAL=50, LOW=10 | jarak memungkinkan priority baru tanpa mengubah kategori lama | missing priority legacy menjadi 50 |
| SDL-003 | Priority menjadi salience GRULE dan resolver input | sorting JSON saja tidak cukup | hasil tidak lagi bergantung query order |
| SDL-004 | Canonical literal menolak silent coercion | type error tidak boleh berubah menjadi keputusan bisnis | adapter lama boleh melakukan coercion terukur |
| SDL-005 | Numeric facts memakai canonical decimal string | menjaga presisi PHP BigDecimal | Go menganggap ini representasi wire resmi, bukan coercion literal |
| SDL-006 | Nullable dan NOT tidak didukung v1 | source saat ini tidak punya kontrak null/NOT yang aman | harus menjadi perubahan schema berikutnya |
| SDL-007 | Date hanya YYYY-MM-DD | lexical GRL comparison valid hanya untuk ISO canonical | tanggal permisif lama harus dinormalisasi sebelum canonical IR |
| SDL-008 | String EQ case-sensitive; CONTAINS case-insensitive Unicode | mempertahankan perilaku Contains lama secara eksplisit | prefix/suffix belum didukung v1 |
| SDL-009 | Empty membership ditolak | false/true otomatis menutupi kesalahan authoring | legacy empty array kini invalid |
| SDL-010 | COLLECT_SUM hanya ADD | SET tidak mempunyai operasi penjumlahan yang masuk akal | mixed target ditolak |
| SDL-011 | PRIORITY tie adalah error | ID database bukan semantik bisnis | author harus memberi priority berbeda atau memilih FIRST |
| SDL-012 | FIRST memakai priority desc lalu stable rule ID asc | array dan DB order tidak stabil | deterministic pada permutation |
| SDL-013 | UNIQUE divalidasi konservatif terhadap potential producer | belum ada satisfiability analyzer | rule mutually exclusive tetap perlu policy lain atau analisis masa depan |
| SDL-014 | SET+ADD target sama ditolak untuk semua policy v1 | menghindari implicit pre/post ordering | perlu migration rule bila data aktif bercampur |
| SDL-015 | Formula diparse menjadi AST | regex tidak cukup sebagai batas injection | grammar sengaja kecil tanpa function call |
| SDL-016 | Money scale 6 HALF_UP | sama dengan helper Go/PHP aktual dan cukup untuk rate payroll | bukan scale 0 seperti contoh konseptual |
| SDL-017 | Canonical hash mengabaikan description dan legacy index | metadata non-eksekusi/permutation tidak mengubah identitas semantik | provenance stable memakai rule ID/version ID |
| SDL-018 | Legacy response index tetap ada, stable provenance ditambahkan | menghindari pemutusan client lama | consumer baru harus memilih version ID/stable ID |
| SDL-019 | Conflict analyzer dipanggil submit, approval, activation | ambiguity harus dihentikan sebelum runtime | periode tidak overlap dan replacement version master sama diperbolehkan |
| SDL-020 | Batas 1 MiB, 500 rules, depth 2, 50 leaves, 8 actions, deadline 5 detik | trust boundary dan resource safety | dapat dinaikkan hanya melalui keputusan schema/operasional eksplisit |

## Keputusan yang masih memerlukan konfirmasi bisnis

1. Apakah policy target perlu disimpan di database/UI, bukan hanya hasil inferensi adapter.
2. Apakah FIRST boleh mengabaikan priority dan hanya memakai stable rule ID; implementasi saat ini mempertahankan priority sebagai ordering primer.
3. Apakah output COLLECT_SUM harus satu component agregat (implementasi saat ini) atau satu row per contributor.
4. Apakah scale 6 adalah final reporting scale atau hanya calculation scale sebelum pembulatan payslip/currency.
5. Apakah nullable facts dan NOT dibutuhkan pada schema 1.1.
