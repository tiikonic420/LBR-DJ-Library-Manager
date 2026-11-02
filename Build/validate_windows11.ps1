param([string]$Python='py', [string]$Payload='')
$ErrorActionPreference='Stop'
$Root=Split-Path $PSScriptRoot -Parent
$Output=Join-Path $Root ('Results\WINDOWS_'+(Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Force -Path $Output | Out-Null
$ArgsPrefix=@()
if ($Python -eq 'py') { $ArgsPrefix=@('-3.13') }
& $Python @ArgsPrefix -c 'import sys; assert sys.version_info[:2]==(3,13); print(sys.version)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.13 requis.' }
& $Python @ArgsPrefix (Join-Path $Root 'Tests\run_local.py') --gui --output $Output
if ($LASTEXITCODE -ne 0) { throw "Tests échoués : $Output" }
& $Python @ArgsPrefix (Join-Path $Root 'Tests\benchmark_catalogue.py') --output (Join-Path $Output 'catalogue.json')
if ($LASTEXITCODE -ne 0) { throw 'Benchmark catalogue échoué.' }
& $Python @ArgsPrefix (Join-Path $Root 'Performance2\benchmark.py') --source (Join-Path $Root 'Sources_application') --output (Join-Path $Output 'gui.json') --sizes '1000,10000' --repeat 3
if ($LASTEXITCODE -ne 0) { throw 'Benchmark graphique échoué.' }
if ($Payload) {
    $Runtime=Join-Path $Payload '_internal\python\python.exe'
    & $Runtime -I -c 'import sys,tkinter,PIL,mutagen,rbsync;assert sys.version_info[:2]==(3,13);print(sys.version)'
    if ($LASTEXITCODE -ne 0) { throw 'Runtime du payload invalide.' }
    & $Runtime -I -m rbsync --help
    if ($LASTEXITCODE -ne 0) { throw 'rbsync --help du payload invalide.' }
}
Write-Host "Tests automatiques terminés : $Output. L'installation/désinstallation, le DPI, les fichiers réellement verrouillés et Sandbox restent à vérifier selon Documentation\VALIDATION_WINDOWS.md."
