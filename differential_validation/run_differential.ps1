$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Bash = (Get-Command bash -ErrorAction Stop).Source
& $Bash (Join-Path $Root 'run_all.sh')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

