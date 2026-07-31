# Menjalankan Branch/Condition Coverage dari Git Bash

Panduan ini khusus untuk proyek `engine-rms` dan dijalankan dari **Git Bash Here** pada folder:

```text
C:\PROJECT\engine-rms
```

## 1. Pastikan terminal berada di folder yang benar

```bash
pwd
```

Output yang diharapkan:

```text
/c/PROJECT/engine-rms
```

Verifikasi Go dan baseline test:

```bash
go version
go test ./... -count=1 -timeout=120s
```

Jangan melanjutkan bila test gagal.

## 2. Instal Gobco

Go bawaan hanya menghasilkan statement coverage. Gunakan Gobco untuk mengukur condition coverage, yaitu outcome `true` dan `false` dari kondisi boolean.

```bash
go install github.com/rillig/gobco@latest
```

Temukan executable yang baru dipasang:

```bash
GO_BIN_RAW="$(go env GOBIN)"

if [ -z "$GO_BIN_RAW" ]; then
    GO_BIN_RAW="$(go env GOPATH)\\bin"
fi

GO_BIN="$(cygpath -u "$GO_BIN_RAW")"
GOBCO="$GO_BIN/gobco.exe"

if [ ! -x "$GOBCO" ]; then
    echo "gobco.exe tidak ditemukan di: $GOBCO" >&2
    exit 1
fi

echo "Gobco: $GOBCO"
go version -m "$GOBCO"
```

Untuk publikasi, simpan output `go version -m`. Setelah versi tervalidasi, gunakan version atau pseudo-version tersebut—bukan `@latest`—pada proses reproduksi berikutnya.

## 3. Jalankan condition coverage

Variabel `$GOBCO` hanya berlaku di terminal tempat variabel itu dibuat. Karena itu, definisikan kembali executable Gobco sebelum menjalankannya:

```bash
GOBCO="$(cygpath -u "$(go env GOPATH)")/bin/gobco.exe"

if [ ! -x "$GOBCO" ]; then
    echo "Gobco belum ditemukan. Menjalankan instalasi..."
    go install github.com/rillig/gobco@latest || exit $?
fi

if [ ! -x "$GOBCO" ]; then
    echo "gobco.exe tetap tidak ditemukan di: $GOBCO" >&2
    exit 1
fi

echo "Menjalankan: $GOBCO"
"$GOBCO" 2>&1 | tee branch-coverage-go.txt
gobco_status=${PIPESTATUS[0]}

if [ "$gobco_status" -ne 0 ]; then
    echo "Gobco gagal dengan exit code $gobco_status" >&2
    exit "$gobco_status"
fi
```

Pada first run, Gobco dapat menampilkan hanya karakter `*` selama beberapa menit. Ini menandakan proses instrumentasi/kompilasi masih berjalan, bukan `command not found`. Tunggu sampai daftar kondisi dan prompt Git Bash muncul kembali. Jangan menempelkan perintah lain selama prompt `$` belum kembali.

Output utama akan berbentuk:

```text
Condition coverage: COVERED/TOTAL
```

Gobco juga menampilkan kondisi yang baru pernah bernilai `true` atau baru pernah bernilai `false`. Kondisi tersebut adalah target penambahan test berikutnya.

## 4. Hitung persentase

```bash
coverage_line="$(grep -m1 -E 'Condition coverage:[[:space:]]*[0-9]+/[0-9]+' branch-coverage-go.txt)"

if [ -z "$coverage_line" ]; then
    echo "Baris Condition coverage tidak ditemukan." >&2
    exit 1
fi

covered="$(printf '%s\n' "$coverage_line" | sed -E 's/.*Condition coverage:[[:space:]]*([0-9]+)\/([0-9]+).*/\1/')"
total="$(printf '%s\n' "$coverage_line" | sed -E 's/.*Condition coverage:[[:space:]]*([0-9]+)\/([0-9]+).*/\2/')"

awk -v covered="$covered" -v total="$total" '
BEGIN {
    percentage = total == 0 ? 0 : (covered / total) * 100
    printf "Condition coverage: %d/%d (%.2f%%)\n", covered, total, percentage
}'
```

Jika hasilnya `93.50%`, redaksi yang tepat adalah:

```text
The test suite achieved 93.5% condition coverage on the Go rule-engine
package, measured using Gobco.
```

Jangan menyebut angka dari `go tool cover -func` sebagai branch coverage.

## 5. Jalankan statement coverage sebagai pendamping

```bash
go test ./... \
    -count=1 \
    -timeout=120s \
    -covermode=count \
    -coverprofile=statement-coverage-go.out

go tool cover -func=statement-coverage-go.out \
    | tee statement-coverage-go.txt

go tool cover \
    -html=statement-coverage-go.out \
    -o statement-coverage-go.html
```

Buka laporan HTML di Windows:

```bash
cmd.exe /c start "" "$(cygpath -w "$PWD/statement-coverage-go.html")"
```

Hasil ini harus diberi label **statement coverage**.

## 6. Simpan evidence run

```bash
{
    echo "Timestamp: $(date --iso-8601=seconds)"
    echo "Commit: $(git rev-parse HEAD)"
    echo "Working tree:"
    git status --short
    echo
    go version
    go version -m "$GOBCO"
    echo
    grep -m1 -E 'Condition coverage:' branch-coverage-go.txt
    grep -E '^total:' statement-coverage-go.txt || true
} | tee coverage-evidence-go.txt
```

Simpan empat artefak berikut bersama commit yang diuji:

```text
branch-coverage-go.txt
statement-coverage-go.out
statement-coverage-go.txt
coverage-evidence-go.txt
```

## 7. Perintah lengkap sekali tempel

Blok berikut melakukan instalasi, test, condition coverage, statement coverage, dan pencatatan evidence:

```bash
set -o pipefail

if [ "$(pwd -W 2>/dev/null)" != "C:/PROJECT/engine-rms" ]; then
    echo "Buka Git Bash langsung di C:\\PROJECT\\engine-rms." >&2
    exit 1
fi

go test ./... -count=1 -timeout=120s || exit $?
go install github.com/rillig/gobco@latest || exit $?

GO_BIN_RAW="$(go env GOBIN)"
if [ -z "$GO_BIN_RAW" ]; then
    GO_BIN_RAW="$(go env GOPATH)\\bin"
fi

GO_BIN="$(cygpath -u "$GO_BIN_RAW")"
GOBCO="$GO_BIN/gobco.exe"

if [ ! -x "$GOBCO" ]; then
    echo "gobco.exe tidak ditemukan di: $GOBCO" >&2
    exit 1
fi

"$GOBCO" 2>&1 | tee branch-coverage-go.txt
gobco_status=${PIPESTATUS[0]}
if [ "$gobco_status" -ne 0 ]; then
    exit "$gobco_status"
fi

go test ./... \
    -count=1 \
    -timeout=120s \
    -covermode=count \
    -coverprofile=statement-coverage-go.out || exit $?

go tool cover -func=statement-coverage-go.out \
    | tee statement-coverage-go.txt
cover_status=${PIPESTATUS[0]}
if [ "$cover_status" -ne 0 ]; then
    exit "$cover_status"
fi

go tool cover \
    -html=statement-coverage-go.out \
    -o statement-coverage-go.html || exit $?

coverage_line="$(grep -m1 -E 'Condition coverage:[[:space:]]*[0-9]+/[0-9]+' branch-coverage-go.txt)"
if [ -z "$coverage_line" ]; then
    echo "Baris Condition coverage tidak ditemukan." >&2
    exit 1
fi

covered="$(printf '%s\n' "$coverage_line" | sed -E 's/.*Condition coverage:[[:space:]]*([0-9]+)\/([0-9]+).*/\1/')"
total="$(printf '%s\n' "$coverage_line" | sed -E 's/.*Condition coverage:[[:space:]]*([0-9]+)\/([0-9]+).*/\2/')"

awk -v covered="$covered" -v total="$total" '
BEGIN {
    percentage = total == 0 ? 0 : (covered / total) * 100
    printf "Condition coverage: %d/%d (%.2f%%)\n", covered, total, percentage
}'

{
    echo "Timestamp: $(date --iso-8601=seconds)"
    echo "Commit: $(git rev-parse HEAD)"
    echo "Working tree:"
    git status --short
    echo
    go version
    go version -m "$GOBCO"
    echo
    printf '%s\n' "$coverage_line"
    grep -E '^total:' statement-coverage-go.txt || true
} | tee coverage-evidence-go.txt

echo
echo "Selesai. Artefak coverage dibuat di $PWD"
```

## 8. Cara membaca hasil

Laporkan secara terpisah:

```text
Condition coverage (Gobco) : COVERED/TOTAL = XX.XX%
Statement coverage (Go)    : XX.X%
Scope                      : package rule-engine
Commit                     : <hash>
Tests                      : pass/fail
```

Gobco tidak mencakup `select` statement dan tidak mendeteksi fungsi tanpa kondisi yang sama sekali tidak pernah dipanggil. Karena itu, persentase condition coverage harus selalu disertai statement coverage dan daftar critical paths yang diuji.
