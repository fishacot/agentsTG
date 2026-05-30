# Install recommended Cursor/VS Code extensions (run from repo root).
# Usage: powershell -ExecutionPolicy Bypass -File scripts/install-cursor-extensions.ps1

$ErrorActionPreference = "Continue"

$extensions = @(
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.debugpy",
    "charliermarsh.ruff",
    "DavidAnson.vscode-markdownlint",
    "tamasfe.even-better-toml",
    "redhat.vscode-yaml",
    "eamodio.gitlens",
    "ms-azuretools.vscode-docker",
    "usernamehw.errorlens"
)

foreach ($id in $extensions) {
    Write-Host "`n=== $id ===" -ForegroundColor Cyan
    cursor --install-extension $id --force
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed: $id (retry or install from Extensions panel)" -ForegroundColor Yellow
    }
}

Write-Host "`nInstalled extensions:" -ForegroundColor Green
cursor --list-extensions
