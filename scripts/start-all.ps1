$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "start-control.ps1")
& py -3 (Join-Path $PSScriptRoot "control_server.py") --action start_all
if ($LASTEXITCODE -ne 0) { throw "Startup request failed." }
