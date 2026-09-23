# SPDX-License-Identifier: GPL-2.0-or-later
# WARNING: erases target Flash; EEPROM may also be erased. Target: Mega2560, 16 MHz.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9]{1,5}$')]
    [ValidateScript({ [int]$_ -ge 1 -and [int]$_ -le 65535 })]
    [string]$SerialNumber,
    [string]$Gateway = '192.168.1.1',
    [string]$Dns = '192.168.1.1',
    [string]$Python,
    [string]$Avrdude,
    [string]$AvrdudeConfig,
    [string]$Port = 'usb',
    [ValidateRange(1, 1000)]
    [int]$BitClock = 10,
    [switch]$SkipTests,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Python = & (Join-Path $PSScriptRoot 'tools/resolvePython.ps1') -Python $Python

if (-not $Avrdude) {
    $toolRoot = Join-Path $env:LOCALAPPDATA 'Arduino15/packages/arduino/tools/avrdude'
    $installed = @(Get-ChildItem -Path "$toolRoot/*/bin/avrdude.exe" -ErrorAction SilentlyContinue | Sort-Object FullName)
    if ($installed.Count) {
        $Avrdude = $installed[-1].FullName
    } else {
        $command = Get-Command avrdude -CommandType Application -ErrorAction SilentlyContinue
        if ($command) { $Avrdude = $command.Source }
    }
}
if (-not $Avrdude) { throw 'avrdude not found. Pass -Avrdude and -AvrdudeConfig.' }
$Avrdude = (Get-Command $Avrdude -CommandType Application -ErrorAction Stop).Source
if (-not $AvrdudeConfig) {
    $candidate = Join-Path (Split-Path (Split-Path $Avrdude -Parent) -Parent) 'etc/avrdude.conf'
    if (Test-Path -LiteralPath $candidate) { $AvrdudeConfig = $candidate }
}
if ($AvrdudeConfig -and -not (Test-Path -LiteralPath $AvrdudeConfig -PathType Leaf)) {
    throw "Missing avrdude configuration: $AvrdudeConfig"
}

# A failed build/test throws before any device is opened, including in DryRun.
$serialText = ([int]$SerialNumber).ToString('D4')
$eeprom = Join-Path $PSScriptRoot "build/provision/$serialText.eep"
& $Python (Join-Path $PSScriptRoot 'tools/provision.py') --serial-number $SerialNumber --gateway $Gateway --dns $Dns --out $eeprom
if ($LASTEXITCODE -ne 0) { throw 'Invalid provisioning data. Programming stopped.' }
& (Join-Path $PSScriptRoot 'build.ps1') -Python $Python -SkipTests:$SkipTests

$ispArguments = @('-p', 'm2560', '-c', 'avrispmkII', '-P', $Port, '-B', "$BitClock")
if ($AvrdudeConfig) { $ispArguments = @('-C', $AvrdudeConfig) + $ispArguments }
$hex = Join-Path $PSScriptRoot 'build/final/bootloader.hex'

function Invoke-ISP {
    param([string]$Label, [string[]]$Arguments)
    Write-Host $Label
    if ($DryRun) {
        # Display only; never evaluate command strings.
        Write-Host ($Avrdude + ' ' + (($ispArguments + $Arguments | ForEach-Object { '"' + $_ + '"' }) -join ' '))
        return
    }
    & $Avrdude @ispArguments @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "avrdude failed ($LASTEXITCODE): $Label. Programming stopped."
    }
}

Write-Host 'Target: ATmega2560, 16 MHz, 8 KiB boot section. Flash will be erased; EEPROM may be erased.'
Invoke-ISP -Label 'Check device signature (no writes)' -Arguments @('-n', '-v')
Invoke-ISP -Label 'Erase and configure fuses' -Arguments @('-e', '-U', 'lfuse:w:0xFF:m', '-U', 'hfuse:w:0xD8:m', '-U', 'efuse:w:0xFD:m')
Invoke-ISP -Label 'Write factory IDLE EEPROM and bootloader; automatically verify both' -Arguments @('-D', '-U', "eeprom:w:${eeprom}:i", '-U', "flash:w:${hex}:i")
Invoke-ISP -Label 'Protect boot section after successful verification' -Arguments @('-U', 'lock:w:0x0F:m')
Invoke-ISP -Label 'Final Flash/EEPROM verification and fuse readback' -Arguments @('-U', "flash:v:${hex}:i", '-U', "eeprom:v:${eeprom}:i", '-U', 'lfuse:r:-:h', '-U', 'hfuse:r:-:h', '-U', 'efuse:r:-:h', '-U', 'lock:r:-:h')
if ($DryRun) {
    Write-Host 'Dry run complete. No programmer or MCU was accessed.'
} else {
    Write-Host 'Bootloader programmed and verified successfully.'
}
