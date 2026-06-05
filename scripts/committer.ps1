# Safe commit helper for Windows (agentsTG).
# Usage:
#   .\scripts\committer.ps1 -Message "fix: inbound dedupe" src/agents_tg/bots/handlers/inbound.py
#   .\scripts\committer.ps1 -Message "docs: update verify" -All
# Refuses commit if .env is staged. Does not push.

param(
    [Parameter(Mandatory = $true)]
    [string]$Message,

    [switch]$All,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Paths
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "=== git status ==="
git status --short

$stagedEnv = git diff --cached --name-only | Where-Object { $_ -match '(^|/)\.env$' }
if ($stagedEnv) {
    Write-Error "Refusing commit: .env is already staged ($stagedEnv)"
}

if ($All) {
    if ($Paths.Count -gt 0) {
        Write-Error "Use either -All or explicit paths, not both."
    }
    Write-Host "=== git add (tracked modifications) ==="
    git add -u
} elseif ($Paths.Count -gt 0) {
    Write-Host "=== git add (explicit paths) ==="
    foreach ($p in $Paths) {
        if ($p -match '(^|/)\.env$') {
            Write-Error "Refusing to stage .env"
        }
        git add -- $p
    }
} else {
    Write-Error "Pass file paths or -All for tracked modifications."
}

$stagedEnv = git diff --cached --name-only | Where-Object { $_ -match '(^|/)\.env$' }
if ($stagedEnv) {
    Write-Error "Refusing commit: .env would be committed ($stagedEnv)"
}

$staged = git diff --cached --name-only
if (-not $staged) {
    Write-Error "Nothing staged — nothing to commit."
}

Write-Host "=== git commit ==="
git commit -m $Message

Write-Host "Done."
