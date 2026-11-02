$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if ($env:GITHUB_ACTIONS -ne 'true' -or -not $env:RUNNER_TEMP) { throw 'Ce provisionnement est réservé au runner GitHub hébergé de validation.' }
$Config=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'ci-tools.json') -Raw | ConvertFrom-Json
$Tools=Join-Path $env:RUNNER_TEMP 'LBR-CI-tools'
New-Item -ItemType Directory -Path $Tools -Force | Out-Null
$Archive=Join-Path $Tools 'ffmpeg-9.0.2-full_build.zip'
if (-not (Test-Path -LiteralPath $Archive)) { Invoke-WebRequest -Uri $Config.ffmpeg_url -OutFile $Archive }
$Hash=(Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($Hash -ne $Config.ffmpeg_archive_sha256) { throw 'Archive FFmpeg non conforme ; aucune exécution autorisée.' }
$Unpacked=Join-Path $Tools 'ffmpeg'
if (-not (Test-Path -LiteralPath $Unpacked)) { Expand-Archive -LiteralPath $Archive -DestinationPath $Unpacked }
$Exe=Join-Path $Unpacked $Config.ffmpeg_executable
if (-not (Test-Path -LiteralPath $Exe)) { throw 'FFmpeg absent de l''archive verifiee.' }
$Version=(& $Exe -version | Select-Object -First 1)
if ($LASTEXITCODE -ne 0 -or $Version -notmatch '^ffmpeg version 9\.0\.2') { throw 'Version FFmpeg incorrecte.' }
Add-Content -LiteralPath $env:GITHUB_PATH -Value (Split-Path $Exe -Parent)
$Log=Join-Path $env:GITHUB_WORKSPACE '.ci-logs'
New-Item -ItemType Directory -Path $Log -Force | Out-Null
@{archive_sha256=$Hash; executable_sha256=(Get-FileHash -LiteralPath $Exe -Algorithm SHA256).Hash; version=$Version; manifest_source=$Config.source_manifest} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $Log 'ffmpeg_provenance.json')
Write-Host $Version
