# SPDX-License-Identifier: GPL-2.0-or-later
# Run from any directory. GNU make is not required.
[CmdletBinding()]
param(
    [string]$Python,
    [switch]$SkipTests
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Python = & (Join-Path $PSScriptRoot 'tools/resolvePython.ps1') -Python $Python

function Invoke-Python {
    param([string[]]$Arguments)
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python failed ($LASTEXITCODE): $($Arguments -join ' ')"
    }
}

Push-Location $PSScriptRoot
try {
    Invoke-Python -Arguments @('tools/build.py', 'final')
    Invoke-Python -Arguments @('tools/report.py')
    if (-not $SkipTests) {
        foreach ($test in @('tools/check_sources.py', 'tests/run.py', 'tests/w5500.py', 'tests/link_limit.py', 'tests/application_build.py')) {
            Invoke-Python -Arguments @($test)
        }
    }
    $size = Get-Content -LiteralPath 'build/final/size.json' -Raw | ConvertFrom-Json
    Write-Host "Build OK: $($size.flash_bytes)/8192 bytes; $($size.flash_free) bytes free."
    Write-Host "HEX: $(Join-Path $PSScriptRoot 'build/final/bootloader.hex')"
} finally {
    Pop-Location
}
