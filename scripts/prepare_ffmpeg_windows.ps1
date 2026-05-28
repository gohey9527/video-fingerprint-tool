# Copy real FFmpeg binaries into build_resources/bin.
# Prefer downloading a static build so Chocolatey shims are never packaged.
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

function Install-StaticFfmpeg {
    $cacheRoot = Join-Path $PSScriptRoot "..\build_resources\.ffmpeg-cache"
    $zipPath = Join-Path $cacheRoot "ffmpeg-win64-gpl.zip"
    $extractRoot = Join-Path $cacheRoot "extracted"
    $url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

    New-Item -ItemType Directory -Force -Path $cacheRoot | Out-Null

    if (-not (Test-Path $zipPath)) {
        Write-Host "Downloading static FFmpeg from BtbN..."
        Invoke-WebRequest -Uri $url -OutFile $zipPath
    }

    if (Test-Path $extractRoot) {
        Remove-Item -Recurse -Force $extractRoot
    }
    Expand-Archive -Path $zipPath -DestinationPath $extractRoot -Force

    $binDir = Get-ChildItem -Path $extractRoot -Recurse -Directory -Filter bin |
        Where-Object { Test-Path (Join-Path $_.FullName "ffmpeg.exe") } |
        Select-Object -First 1

    if (-not $binDir) {
        return $false
    }

    if (Copy-BinDirectory $binDir.FullName) {
        Write-Host "Copied FFmpeg from static build: $($binDir.FullName)"
        return $true
    }
    return $false
}

if (Install-StaticFfmpeg) {
    exit 0
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

Write-Error "Unable to locate a real ffmpeg.exe binary with all required DLLs."
