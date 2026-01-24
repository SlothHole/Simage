tools/launch-agent.#requires -Version 7.0
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

param(
    [Parameter(Mandatory)]
    [ValidateSet('implementer', 'manager', 'coder')]
    [string]$Role,

    [string]$DiffPath
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')

$agentsDir = Join-Path $repoRoot 'docs\agents'

$resetGate = Join-Path $agentsDir 'AGENT_RESET_GATE.md'

switch ($Role) {
    'implementer' { $rolePrompt = 'AGENT_PROMPT.md' }
    'manager' { $rolePrompt = 'AGENT_PROMPT_MANAGER.md' }
    'coder' { $rolePrompt = 'AGENT_PROMPT_CODING.md' }
}

$rolePromptPath = Join-Path $agentsDir $rolePrompt

if (-not (Test-Path $resetGate)) {
    throw "Missing AGENT_RESET_GATE.md"
}

if (-not (Test-Path $rolePromptPath)) {
    throw "Missing $rolePrompt"
}

Write-Host ""
Write-Host "=== AGENT LAUNCH ==="
Write-Host "Role: $Role"
Write-Host ""

Write-Host "----- RESET GATE -----"
Get-Content $resetGate
Write-Host ""

Write-Host "----- ROLE PROMPT ($rolePrompt) -----"
Get-Content $rolePromptPath
Write-Host ""

if ($DiffPath) {
    if (-not (Test-Path $DiffPath)) {
        throw "DIFF not found: $DiffPath"
    }

    Write-Host "----- DIFF INPUT ($DiffPath) -----"
    Get-Content $DiffPath
    Write-Host ""
}

Write-Host "----- END INPUT -----"
Write-Host ""
Write-Host "Paste the above into the agent and await response."
