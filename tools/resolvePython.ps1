# SPDX-License-Identifier: GPL-2.0-or-later
param([string]$Python)
if ($Python) { return $Python }
foreach ($name in @('python', 'python3', 'py')) {
    $command = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
}
throw 'Python 3 not found. Pass -Python C:\path\to\python.exe.'
