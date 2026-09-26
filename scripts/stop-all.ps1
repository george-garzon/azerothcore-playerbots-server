param([ValidateRange(10,300)][int]$Countdown = 60)
$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "start-control.ps1")
& py -3 (Join-Path $PSScriptRoot "control_server.py") --action stop_all --countdown $Countdown
if ($LASTEXITCODE -ne 0) { throw "Shutdown request failed." }
