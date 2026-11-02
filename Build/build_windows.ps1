param([switch]$AllowDownloads, [switch]$CompileInstaller, [switch]$CompileMsi)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Root = Split-Path $PSScriptRoot -Parent
$Work = Join-Path $Root '.build-windows'
$Venv = Join-Path $Work 'venv313'
$Python = Join-Path $Venv 'Scripts\python.exe'
$Payload = Join-Path $Work 'payload'
if (Test-Path $Payload) { throw "Le dossier de compilation existe déjà : $Payload. Archivez-le ou choisissez une copie neuve du projet." }
New-Item -ItemType Directory -Force -Path $Work | Out-Null
if (-not (Test-Path $Python)) {
    & py -3.13 -m venv $Venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.13 avec Tcl/Tk doit être installé.' }
}
if ($AllowDownloads) {
    & $Python -m pip install -r (Join-Path $PSScriptRoot 'requirements-windows.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Échec des dépendances Python 3.13 ; aucun installateur créé.' }
    & $Python -m pip install (Join-Path $Root 'Licences\rbsync-source.zip')
    if ($LASTEXITCODE -ne 0) { throw 'Échec de rbsync depuis les sources fournies.' }
} else {
    Write-Host 'Aucun téléchargement autorisé. Utilisation des dépendances déjà présentes dans le venv isolé.'
}
& $Python -c "import sys,tkinter,PIL,mutagen,rbsync,pyrekordbox,sqlcipher3; assert sys.version_info[:2]==(3,13); print('Python 3.13 et imports OK')"
if ($LASTEXITCODE -ne 0) { throw 'Dépendances manquantes. Préparez le venv ou relancez avec -AllowDownloads pour autoriser pip.' }
& $Python (Join-Path $Root 'Tests\run_local.py') --gui --output (Join-Path $Work 'validation-sources')
if ($LASTEXITCODE -ne 0) { throw 'Tests sources échoués. Compilation bloquée.' }
$Base = (& $Python -c 'import sys;print(sys.base_prefix)').Trim()
$Site = Join-Path $Venv 'Lib\site-packages'
$Runtime = Join-Path $Payload '_internal\python'
$App = Join-Path $Payload '_internal\app'
New-Item -ItemType Directory -Force -Path $Runtime,$App | Out-Null
foreach ($Name in @('python.exe','pythonw.exe','python313.dll','python3.dll','vcruntime140.dll','vcruntime140_1.dll','LICENSE.txt')) {
    $From = Join-Path $Base $Name
    if (Test-Path $From) { Copy-Item $From $Runtime }
}
foreach ($Name in @('Lib','DLLs','tcl')) {
    if ($Name -eq 'Lib') {
        New-Item -ItemType Directory -Force -Path (Join-Path $Runtime 'Lib') | Out-Null
        Get-ChildItem (Join-Path $Base 'Lib') -Exclude 'site-packages' | Copy-Item -Destination (Join-Path $Runtime 'Lib') -Recurse
    } else { Copy-Item (Join-Path $Base $Name) (Join-Path $Runtime $Name) -Recurse }
}
$RuntimeSite = Join-Path $Runtime 'Lib\site-packages'
if (Test-Path $RuntimeSite) { Remove-Item $RuntimeSite -Recurse -Force }
Copy-Item $Site $RuntimeSite -Recurse
Copy-Item (Join-Path $Root 'Sources_application\*') $App -Recurse
$Compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $Compiler)) { throw 'Compilateur .NET Framework x64 Windows absent.' }
& $Compiler /nologo /target:winexe /platform:x64 /optimize+ "/win32icon:$(Join-Path $Root 'Sources_application\assets\lbr.ico')" "/out:$(Join-Path $Payload 'LBR_DJ_Library_Manager.exe')" /reference:System.Windows.Forms.dll (Join-Path $PSScriptRoot 'Launcher.cs')
if ($LASTEXITCODE -ne 0) { throw 'Compilation du lanceur x64 échouée.' }
Copy-Item (Join-Path $Root 'Documentation') $Payload -Recurse
Copy-Item (Join-Path $Root 'Licences') $Payload -Recurse
& (Join-Path $Runtime 'python.exe') -I -c 'import sys,tkinter,PIL,mutagen,rbsync,pyrekordbox; assert sys.version_info[:2]==(3,13); print(sys.version)'
if ($LASTEXITCODE -ne 0) { throw 'Runtime copié non utilisable : packaging bloqué.' }
& (Join-Path $Runtime 'python.exe') -I -m rbsync --help
if ($LASTEXITCODE -ne 0) { throw 'CLI rbsync non fonctionnelle : packaging bloqué.' }
& $Python -m pip freeze | Set-Content -Encoding utf8 (Join-Path $Payload 'DEPENDANCES_INSTALLEES.txt')
$Version = (& $Python -c 'import runpy,sys;print(runpy.run_path(sys.argv[1])["VERSION"])' (Join-Path $Root 'Sources_application\release_info.py')).Trim()
$PythonVersion = (& $Python -c 'import platform;print(platform.python_version())').Trim()
$RbsyncVersion = (& $Python -c 'import importlib.metadata as m;print(m.version("rekordbox-playlist-sync"))').Trim()
$RbsyncSourceHash = (Get-FileHash (Join-Path $Root 'Licences\rbsync-source.zip') -Algorithm SHA256).Hash.ToLowerInvariant()
@{version=$Version; revision='R10'; runtime='Python 3.13'; python_version=$PythonVersion; rbsync_version=$RbsyncVersion; rbsync_source_sha256=$RbsyncSourceHash; tests_sources='passed'; windows_manual='pending'; launcher='x64 .NET Framework Windows; PE version 5.0.10.1'} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $Payload 'VERSIONS.json')
Get-ChildItem $Payload -File -Recurse | ForEach-Object { $h=Get-FileHash $_.FullName -Algorithm SHA256; "$($h.Hash)  $($_.FullName.Substring($Payload.Length+1))" } | Set-Content -Encoding utf8 (Join-Path $Work 'SHA256_PAYLOAD.txt')
if ($CompileInstaller) {
    $NSIS = Get-Command makensis.exe -ErrorAction SilentlyContinue
    if (-not $NSIS) { throw 'NSIS absent. Payload prêt ; aucun Setup compilé.' }
    $Numeric = (($Version -split ' ')[0]+'.0.0')
    Push-Location (Join-Path $Root 'Sources_installateur')
    try {
        & $NSIS.Source "/DPAYLOAD_DIR=$Payload" "/DRELEASE_TAG=$Version" "/DNUMERIC_VERSION=$Numeric" installer.nsi
        if ($LASTEXITCODE -ne 0) { throw 'Compilation NSIS échouée.' }
    } finally { Pop-Location }
}
if ($CompileMsi) {
    $Distribution = Join-Path $Root 'Distribution'
    New-Item -ItemType Directory -Force -Path $Distribution | Out-Null
    & $Python (Join-Path $PSScriptRoot 'build_msi.py') --payload $Payload --output (Join-Path $Distribution 'LBR_DJ_Library_Manager_5.0_RC_R10_Setup.msi') --work (Join-Path $Work 'cab-msi')
    if ($LASTEXITCODE -ne 0) { throw 'Construction MSI échouée ; conserver le journal.' }
}
Write-Host "Payload préparé : $Payload. Validation manuelle Windows 11 et Sandbox encore requise."
