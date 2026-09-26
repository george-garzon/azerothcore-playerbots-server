param(
    [switch]$Install,
    [string]$Model = "llama3.2:3b"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$OllamaRoot = Join-Path $RepoRoot "var/ollama"
$Executable = Join-Path $OllamaRoot "runtime/ollama.exe"
New-Item -ItemType Directory -Force $OllamaRoot | Out-Null

if (-not (Test-Path -LiteralPath $Executable)) {
    if (-not $Install) { throw "Run .\scripts\start-ollama.ps1 -Install first (downloads Windows Ollama)." }
    $Archive = Join-Path $OllamaRoot "ollama-windows-amd64.zip"
    & curl.exe -L --fail --show-error https://github.com/ollama/ollama/releases/download/v0.34.4/ollama-windows-amd64.zip -o $Archive
    if ($LASTEXITCODE -ne 0) { throw "Ollama download failed." }
    Expand-Archive -LiteralPath $Archive -DestinationPath (Join-Path $OllamaRoot "runtime") -Force
}

$Signature = Get-AuthenticodeSignature -FilePath $Executable
if ($Signature.Status -ne "Valid" -or $Signature.SignerCertificate.Subject -notmatch 'Ollama Inc\.') {
    throw "Ollama executable did not pass publisher signature verification."
}

$env:OLLAMA_HOST = "127.0.0.1:11434"
$env:OLLAMA_MODELS = Join-Path $OllamaRoot "models"
$env:OLLAMA_VULKAN = "1"
$env:GGML_VK_VISIBLE_DEVICES = "1" # RX 9060 XT on this host; Vulkan0 is the iGPU.
$env:OLLAMA_NUM_PARALLEL = "1"
$env:OLLAMA_MAX_LOADED_MODELS = "1"
$env:OLLAMA_CONTEXT_LENGTH = "4096"
$env:OLLAMA_KEEP_ALIVE = "30m"
$env:OLLAMA_NO_CLOUD = "1"

$Ready = $false
try { $null = Invoke-RestMethod http://127.0.0.1:11434/api/version -TimeoutSec 2; $Ready = $true } catch { }
if (-not $Ready) {
    $Process = Start-Process -FilePath $Executable -ArgumentList "serve" -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $OllamaRoot "serve.out.log") `
        -RedirectStandardError (Join-Path $OllamaRoot "serve.err.log")
    Set-Content -LiteralPath (Join-Path $OllamaRoot "serve.pid") -Value $Process.Id
    for ($Attempt = 0; $Attempt -lt 30; $Attempt++) {
        Start-Sleep -Seconds 1
        try { $null = Invoke-RestMethod http://127.0.0.1:11434/api/version -TimeoutSec 2; $Ready = $true; break } catch { }
        if ($Process.HasExited) { break }
    }
    if (-not $Ready) { throw "Ollama did not start. Check var/ollama/serve.err.log." }
} else {
    Write-Host "Using the existing Ollama listener; its process settings are unchanged."
}

$InstalledModels = (Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 5).models
if (-not ($InstalledModels | Where-Object { $_.name -eq $Model -or $_.name -eq "${Model}:latest" })) {
    & $Executable pull $Model
    if ($LASTEXITCODE -ne 0) { throw "Could not download model $Model." }
}
Write-Host "Ollama ready at http://127.0.0.1:11434 (Docker: host.docker.internal:11434)."
Write-Host "Check GPU after a reply: & '$Executable' ps"
