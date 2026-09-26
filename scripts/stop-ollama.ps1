$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$OllamaRoot = Join-Path $RepoRoot "var/ollama"
$PidFile = Join-Path $OllamaRoot "serve.pid"
if (-not (Test-Path -LiteralPath $PidFile)) { Write-Host "No managed Ollama process recorded."; return }
$OllamaProcessId = [int](Get-Content -LiteralPath $PidFile)
$Process = Get-Process -Id $OllamaProcessId -ErrorAction SilentlyContinue
if ($Process) {
    $ExpectedPath = [IO.Path]::GetFullPath((Join-Path $OllamaRoot "runtime/ollama.exe"))
    if ($Process.Path -ne $ExpectedPath) { throw "Recorded PID belongs to another program; refusing to stop it." }
    Stop-Process -Id $OllamaProcessId
}
Remove-Item -LiteralPath $PidFile
Write-Host "Stopped this project's Ollama server."
