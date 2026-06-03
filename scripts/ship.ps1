# Local ship: verify -> optional commit message via env -> push -> VPS deploy
# Usage:
#   $env:COMMIT_MSG = "feat: MVP manus parity batch"
#   $env:VPS_SSH_PASSWORD = "..."   # required for deploy
#   .\scripts\ship.ps1

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$logDir = "docs"
$pytestLog = Join-Path $logDir "last_pytest_run.txt"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

Write-Host "=== black / isort ==="
python -m black src tests
python -m isort src tests

Write-Host "=== pytest ==="
python -m pytest tests/ -q --tb=short 2>&1 | Tee-Object -FilePath $pytestLog
if ($LASTEXITCODE -ne 0) {
    Write-Host "pytest FAILED — see $pytestLog"
    exit $LASTEXITCODE
}

if ($env:COMMIT_MSG) {
    Write-Host "=== git commit ==="
    git add -A
    git reset HEAD -- "ответ на промт*.md" 2>$null
    git reset HEAD -- "scripts/_patch_resource_mitigations.py" 2>$null
    git commit -m $env:COMMIT_MSG
}

if ($env:SKIP_PUSH -ne "1") {
    Write-Host "=== git push ==="
    git push origin HEAD
}

if ($env:VPS_SSH_PASSWORD) {
    Write-Host "=== VPS deploy ==="
    python scripts/vps_deploy.py 2>&1 | Tee-Object -FilePath (Join-Path $logDir "last_vps_deploy.txt")
} else {
    Write-Host "SKIP deploy: set VPS_SSH_PASSWORD"
}

Write-Host "Done."
