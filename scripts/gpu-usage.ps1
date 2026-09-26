$ErrorActionPreference = "Stop"
$RuntimePath = [IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $PSScriptRoot) "var/ollama/runtime"))
# Ollama's model runner is a separate executable, not always named ollama.exe.
$OllamaIds = @(Get-CimInstance Win32_Process | Where-Object {
    $_.ExecutablePath -and $_.ExecutablePath.StartsWith($RuntimePath + '\', [StringComparison]::OrdinalIgnoreCase)
} | Select-Object -ExpandProperty ProcessId)
if ($OllamaIds.Count -eq 0) { Write-Output 0; return }
$Counters = Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine
$Values = @($Counters | Where-Object {
    $_.Name -match '^pid_(\d+)_' -and [int]$Matches[1] -in $OllamaIds
} | Select-Object -ExpandProperty UtilizationPercentage)
if ($Values.Count -eq 0) { throw "No GPU engine counters for Ollama" }
Write-Output ([Math]::Min(100, ($Values | Measure-Object -Maximum).Maximum))
