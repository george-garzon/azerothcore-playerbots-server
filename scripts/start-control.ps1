$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
try {
    $null = Invoke-RestMethod http://127.0.0.1:8765/api/session -TimeoutSec 2
    Write-Host "Control dashboard: http://127.0.0.1:8765"
    return
} catch { }
$Python = (& py -3 -c "import sys; print(sys.executable)").Trim()
if ($LASTEXITCODE -ne 0) { throw "Python 3 is required." }
$LogPath = Join-Path $RepoRoot "var/control"
New-Item -ItemType Directory -Force $LogPath | Out-Null
$ScriptPath = Join-Path $PSScriptRoot "control_server.py"
$ControllerProcess = Start-Process -FilePath $Python -ArgumentList @('"' + $ScriptPath + '"') -WorkingDirectory $RepoRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $LogPath "stdout.log") -RedirectStandardError (Join-Path $LogPath "stderr.log")
Set-Content -LiteralPath (Join-Path $LogPath "controller.pid") -Value $ControllerProcess.Id
for ($Attempt = 0; $Attempt -lt 15; $Attempt++) {
    Start-Sleep -Seconds 1
    try { $null = Invoke-RestMethod http://127.0.0.1:8765/api/session -TimeoutSec 2; Write-Host "Control dashboard: http://127.0.0.1:8765"; return } catch { }
}
throw "Control service failed to start. Check var/control/stderr.log."
