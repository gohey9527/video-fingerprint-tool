# Copy real FFmpeg binaries (not Chocolatey shims) into build_resources/bin.
$ErrorActionPreference = "Stop"

$target = Join-Path $PSScriptRoot "..\build_resources\bin"
New-Item -ItemType Directory -Force -Path $target | Out-Null
$target = (Resolve-Path $target).Path

function Test-RealFfmpeg {
    param([string]$ExePath)
    if (-not (Test-Path $ExePath)) { return $false }
    & $ExePath -version *> $null
    return $LASTEXITCODE -eq 0
}

function Copy-BinDirectory {
    param([string]$SourceDir)
    if (-not (Test-Path $SourceDir)) { return $false }
    Get-ChildItem -Path $SourceDir -File | Copy-Item -Destination $target -Force
    $copied = Join-Path $target "ffmpeg.exe"
    return (Test-RealFfmpeg $copied)
}

function Add-CandidateDir {
    param([System.Collections.Generic.List[string]]$List, [string]$Dir)
    if ($Dir -and (Test-Path $Dir) -and -not $List.Contains($Dir)) {
        [void]$List.Add($Dir)
    }
}

$candidateDirs = New-Object 'System.Collections.Generic.List[string]'

if ($env:ChocolateyInstall) {
    $chocoRoot = Join-Path $env:ChocolateyInstall "lib\ffmpeg\tools"
    Get-ChildItem -Path $chocoRoot -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue |
        ForEach-Object { Add-CandidateDir $candidateDirs $_.DirectoryName }
}

$commonDirs = @(
    "C:\ffmpeg\bin",
    "C:\Program Files\ffmpeg\bin",
    "C:\tools\ffmpeg\bin"
)
foreach ($dir in $commonDirs) {
    Add-CandidateDir $candidateDirs $dir
}

try {
    $cmd = Get-Command ffmpeg -ErrorAction Stop
    $cmdDir = Split-Path $cmd.Source
    if ($cmdDir -notmatch '\\chocolatey\\bin$') {
        Add-CandidateDir $candidateDirs $cmdDir
    }
} catch {
    # ignore, other candidates may still work
}

foreach ($dir in $candidateDirs) {
    if (Copy-BinDirectory $dir) {
        Write-Host "Copied FFmpeg from: $dir"
        exit 0
    }
}

Write-Error "Unable to locate a real ffmpeg.exe binary with all required DLLs (Chocolatey shims are not supported)."
