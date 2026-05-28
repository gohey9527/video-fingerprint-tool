# Copy full FFmpeg runtime directory (including DLLs) for Windows packaging.
$ErrorActionPreference = "Stop"

$target = Join-Path $PSScriptRoot "..\build_resources\bin"
New-Item -ItemType Directory -Force -Path $target | Out-Null

function Copy-BinDirectory {
    param([string]$SourceDir)
    if (-not (Test-Path $SourceDir)) { return $false }
    Get-ChildItem -Path $SourceDir -File | Copy-Item -Destination $target -Force
    return (Test-Path (Join-Path $target "ffmpeg.exe"))
}

$resolved = $null
try {
    $resolved = (Get-Command ffmpeg -ErrorAction Stop).Source
} catch {
    Write-Error "ffmpeg not found in PATH"
}

if (Copy-BinDirectory (Split-Path $resolved)) {
    Write-Host "Copied FFmpeg from PATH: $resolved"
    exit 0
}

$chocoLib = Join-Path $env:ChocolateyInstall "lib\ffmpeg\tools"
$chocoExe = Get-ChildItem -Path $chocoLib -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue | Select-Object -First 1
if ($chocoExe -and (Copy-BinDirectory $chocoExe.DirectoryName)) {
    Write-Host "Copied FFmpeg from Chocolatey: $($chocoExe.FullName)"
    exit 0
}

Write-Error "Unable to locate full FFmpeg directory (ffmpeg.exe and DLL dependencies required)"
