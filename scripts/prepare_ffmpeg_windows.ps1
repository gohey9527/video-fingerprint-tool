# 复制 FFmpeg 完整运行目录（含所有 DLL），避免 Windows 打包后 ffmpeg 无法启动
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
    Write-Error "未找到 ffmpeg，请先安装 FFmpeg 并加入 PATH"
}

if (Copy-BinDirectory (Split-Path $resolved)) {
    Write-Host "已从 PATH 复制 FFmpeg: $resolved"
    exit 0
}

$chocoLib = Join-Path $env:ChocolateyInstall "lib\ffmpeg\tools"
$chocoExe = Get-ChildItem -Path $chocoLib -Recurse -Filter ffmpeg.exe -ErrorAction SilentlyContinue | Select-Object -First 1
if ($chocoExe -and (Copy-BinDirectory $chocoExe.DirectoryName)) {
    Write-Host "已从 Chocolatey 复制 FFmpeg: $($chocoExe.FullName)"
    exit 0
}

Write-Error "无法定位完整的 FFmpeg 目录（需要 ffmpeg.exe 及依赖 DLL）"
