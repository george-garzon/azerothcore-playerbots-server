$ErrorActionPreference = "Stop"
function Test-DockerReady {
    $ErrorActionPreference = "Continue"
    docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
}
if (Test-DockerReady) { return }
$DockerDesktop = Join-Path $env:ProgramFiles "Docker/Docker/Docker Desktop.exe"
if (-not (Test-Path -LiteralPath $DockerDesktop)) { throw "Install Docker Desktop with Linux containers first." }
Start-Process -FilePath $DockerDesktop -WindowStyle Hidden
for ($Attempt = 0; $Attempt -lt 60; $Attempt++) {
    Start-Sleep -Seconds 2
    if (Test-DockerReady) { return }
}
throw "Docker Desktop did not become ready within two minutes."
