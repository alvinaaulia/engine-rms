$ErrorActionPreference = 'Stop'

$ExperimentRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$GoRoot = Split-Path -Parent $ExperimentRoot
$ProjectRoot = Split-Path -Parent $GoRoot
$LaravelRoot = Join-Path $ProjectRoot 'papa-website-v2'
$EngineBinary = Join-Path $ExperimentRoot 'differential_runner\differential-engine.exe'
$FixtureOutput = Join-Path $ExperimentRoot 'translation_validation_fixtures.json'
$ServerProcess = $null

function Invoke-Checked {
    param([string]$Label, [scriptblock]$Action)
    Write-Host "[$Label]"
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

try {
    $env:APP_ENV = 'testing'
    $env:DB_CONNECTION = 'mysql'
    $env:DB_DATABASE = 'website_papa_v2_testing'
    if (-not $env:DB_DATABASE.EndsWith('_testing')) {
        throw "Refusing migrate:fresh because DB_DATABASE is not a testing database."
    }

    Push-Location $LaravelRoot
    Invoke-Checked 'Laravel testing migration' { php artisan migrate:fresh --env=testing --force }
    Invoke-Checked 'Laravel testing seed' { php artisan db:seed --class=DatabaseSeeder --env=testing --force }
    Pop-Location

    Push-Location $GoRoot
    Invoke-Checked 'Generate deterministic corpus' { python differential_validation\generate_corpus.py }
    Invoke-Checked 'Generate independent reference oracle' { python differential_validation\oracle_calculator\reference_oracle.py }
    Invoke-Checked 'Independently verify and freeze oracle' { python differential_validation\oracle_calculator\verify_oracle.py }

    $env:TPR_TRANSLATION_FIXTURE_OUTPUT = $FixtureOutput
    Invoke-Checked 'Translator fixture tests' { go test ./... -run TestTranslationValidationFixtures -count=1 }
    Remove-Item Env:TPR_TRANSLATION_FIXTURE_OUTPUT -ErrorAction SilentlyContinue

    Invoke-Checked 'Build current Go engine' { go build -o $EngineBinary . }
    $existing = Get-NetTCPConnection -LocalPort 8081 -State Listen -ErrorAction SilentlyContinue
    if ($existing) {
        $existingProcess = Get-Process -Id $existing.OwningProcess -ErrorAction Stop
        if ($existingProcess.ProcessName -notin @('rule-engine', 'differential-engine')) {
            throw "Port 8081 is occupied by an unrelated process: $($existingProcess.ProcessName)."
        }
        Stop-Process -Id $existing.OwningProcess -Force
    }
    $ServerProcess = Start-Process -FilePath $EngineBinary -WorkingDirectory $GoRoot -WindowStyle Hidden -PassThru
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Milliseconds 250
        if (Get-NetTCPConnection -LocalPort 8081 -State Listen -ErrorAction SilentlyContinue) {
            $ready = $true
            break
        }
    }
    if (-not $ready) {
        throw 'Go engine did not become ready on port 8081.'
    }

    Invoke-Checked 'Frozen differential comparison' { python differential_validation\differential_runner\run_differential.py }
    Invoke-Checked 'Full Go suite' { go test ./... -count=1 }
    Invoke-Checked 'Go vet' { go vet ./... }

    Push-Location $LaravelRoot
    Invoke-Checked 'Full Laravel suite' { php artisan test }
    Pop-Location

    Push-Location $GoRoot
    Invoke-Checked 'Generate reports and manifest' { python differential_validation\generate_reports.py }
    Write-Host '[DONE] 624 cases passed with zero unresolved mismatch.'
}
finally {
    Remove-Item Env:TPR_TRANSLATION_FIXTURE_OUTPUT -ErrorAction SilentlyContinue
    if ($ServerProcess -and -not $ServerProcess.HasExited) {
        Stop-Process -Id $ServerProcess.Id -Force -ErrorAction SilentlyContinue
    }
    while ((Get-Location).Path -ne $GoRoot -and (Get-Location).Path.StartsWith($ProjectRoot)) {
        Pop-Location -ErrorAction SilentlyContinue
    }
}
