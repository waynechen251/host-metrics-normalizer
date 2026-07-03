$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $RepoRoot
Write-Host "Set-Location $RepoRoot"


pip install -r "$RepoRoot\requirements.txt"

pyinstaller --clean --noconfirm packaging/windows/host-metrics-normalizer.spec

$ExampleConfig = Join-Path $RepoRoot "configs/config.example.yml"
$DistConfig = Join-Path $RepoRoot "dist/config.example.yml"
Copy-Item -Path $ExampleConfig -Destination $DistConfig -Force

$ExePath = Join-Path $RepoRoot "dist/host-metrics-normalizer.exe"
Write-Host ""
Write-Host "Build complete: $ExePath"
Write-Host "Copy dist/config.example.yml to dist/config.yml (or place a config.yml next to the exe) before running."
