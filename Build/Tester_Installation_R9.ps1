param([string]$Livraison=$PSScriptRoot, [string]$Resultats='C:\LBRResultats', [switch]$ProfilDeTestConfirme)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if ($env:USERNAME -ne 'WDAGUtilityAccount' -and -not $ProfilDeTestConfirme) {
    throw 'Utiliser Windows Sandbox ou un profil Windows de test dédié confirmé avec -ProfilDeTestConfirme. Aucun test dans le profil musical personnel.'
}
$Msi=Join-Path $Livraison 'LBR_DJ_Library_Manager_5.0_RC_R9_Setup.msi'
$Manifest=Get-Content -LiteralPath ([IO.Path]::ChangeExtension($Msi,'.manifest.json')) -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath $Msi -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Manifest.msi_sha256) { throw 'Empreinte MSI incorrecte.' }
$Install=Join-Path $env:LOCALAPPDATA 'Programs\LBR Software\LBR DJ Library Manager R9'
if (Test-Path -LiteralPath $Install) { throw 'R9 est déjà présente ; utiliser un environnement de test neuf.' }
New-Item -ItemType Directory -Path $Resultats -Force | Out-Null
Start-Transcript -LiteralPath (Join-Path $Resultats 'validation_installation.log')
$Installed=$false
$Process=$null
$Child=$null
$Second=$null
$OldEnvironment=@{}
$Checks=[System.Collections.Generic.List[string]]::new()
function Require([bool]$Value,[string]$Name) { if (-not $Value) { throw "ÉCHEC : $Name" }; $Checks.Add($Name); Write-Host "RÉUSSI : $Name" }
function Installer([string]$Action,[string]$Name) {
    $InstallArguments=@($Action,('"{0}"' -f $Msi),'/qn','/norestart','/L*v',('"{0}"' -f (Join-Path $Resultats $Name)))
    $Operation=Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\msiexec.exe') -ArgumentList $InstallArguments -PassThru -Wait -WindowStyle Hidden
    Require ($Operation.ExitCode -eq 0) "$Action : Windows Installer retourne 0"
}
try {
    Installer '/i' 'installation_msi.log'; $Installed=$true
    foreach ($Item in $Manifest.file_index) {
        $File=Join-Path $Install $Item.relative
        if (-not (Test-Path -LiteralPath $File -PathType Leaf)) { throw "Fichier absent : $File" }
        if ((Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Item.sha256) { throw "Fichier différent : $File" }
    }
    Require $true 'Tous les fichiers installés correspondent au manifeste'
    $Exe=Join-Path $Install 'LBR_DJ_Library_Manager.exe'
    $Shell=New-Object -ComObject WScript.Shell
    $Menu=Join-Path ([Environment]::GetFolderPath('Programs')) 'LBR Software'
    foreach ($Link in @((Join-Path $Menu 'LBR DJ Library Manager R9.lnk'),(Join-Path ([Environment]::GetFolderPath('DesktopDirectory')) 'LBR DJ Library Manager R9.lnk'))) {
        Require (Test-Path -LiteralPath $Link) "Raccourci présent : $Link"
        Require ($Shell.CreateShortcut($Link).TargetPath -eq $Exe) 'Le raccourci cible le bon programme'
    }
    $UninstallLink=Join-Path $Menu 'Désinstaller LBR R9.lnk'
    Require (Test-Path -LiteralPath $UninstallLink) 'Raccourci de désinstallation présent'
    Require ($Shell.CreateShortcut($UninstallLink).Arguments -eq ('/x '+$Manifest.product_code)) 'Commande de désinstallation correcte'
    $Profile=Join-Path $Resultats 'Profil fictif été avec espaces'
    New-Item -ItemType Directory -Force -Path $Profile | Out-Null
    foreach ($Key in @('HOME','USERPROFILE','APPDATA','LOCALAPPDATA','LBR_TEST_MODE','PYTHONDONTWRITEBYTECODE')) { $OldEnvironment[$Key]=[Environment]::GetEnvironmentVariable($Key,'Process') }
    foreach ($Key in @('HOME','USERPROFILE','APPDATA','LOCALAPPDATA')) { [Environment]::SetEnvironmentVariable($Key,$Profile,'Process') }
    $env:LBR_TEST_MODE='1'; $env:PYTHONDONTWRITEBYTECODE='1'
    $Python=Join-Path $Install '_internal\python\python.exe'
    & $Python -I (Join-Path $Livraison 'fixture_sauvegarde_R9.py') (Join-Path $Install '_internal\app') $Profile
    Require ($LASTEXITCODE -eq 0) 'Sauvegarde vérifiée sur un WAV fictif avec chemin accentué'
    $Process=Start-Process -FilePath $Exe -PassThru -WindowStyle Hidden
    $End=(Get-Date).AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 100
        $Children=@(Get-CimInstance Win32_Process -Filter "ParentProcessId=$($Process.Id)")
        if ($Children.Count) { $Child=Get-Process -Id $Children[0].ProcessId -ErrorAction SilentlyContinue }
        if ($Child) { $Child.Refresh() }
    } until (($Child -and $Child.MainWindowHandle -ne 0) -or (Get-Date) -gt $End)
    Require ($null -ne $Child -and $Child.MainWindowTitle.StartsWith('LBR DJ Library Manager')) 'Programme installé lancé'
    Require (-not $Child.MainWindowTitle.Contains('Bibliothèque et sécurité')) 'Fenêtre facultative non ouverte au démarrage'
    $Second=Start-Process -FilePath $Exe -PassThru -WindowStyle Hidden
    $End=(Get-Date).AddSeconds(15)
    do { Start-Sleep -Milliseconds 100; $Second.Refresh() } until ($Second.MainWindowHandle -ne 0 -or $Second.HasExited -or (Get-Date) -gt $End)
    Require (-not $Second.HasExited -and $Second.MainWindowHandle -ne 0) 'Seconde instance refusée avec message'
    $null=$Second.CloseMainWindow(); Require ($Second.WaitForExit(10000) -and $Second.ExitCode -eq 2) 'Mutex : seconde instance arrêtée avec code 2'
    $null=$Child.CloseMainWindow(); Require ($Process.WaitForExit(15000) -and $Process.ExitCode -eq 0) 'Fermeture normale sans tâche interrompue'
    $Before=@{}; Get-ChildItem -LiteralPath $Profile -File -Recurse | ForEach-Object { $Before[$_.FullName]=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
    foreach ($Key in $OldEnvironment.Keys) { [Environment]::SetEnvironmentVariable($Key,$OldEnvironment[$Key],'Process') }
    Installer '/x' 'desinstallation_msi.log'; $Installed=$false
    Require (-not (Test-Path -LiteralPath $Exe)) 'Programme retiré après désinstallation'
    Require (-not (Test-Path -LiteralPath (Join-Path $Menu 'LBR DJ Library Manager R9.lnk'))) 'Raccourci du menu retiré'
    foreach ($File in $Before.Keys) { Require ((Test-Path -LiteralPath $File) -and (Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash -eq $Before[$File]) "Donnée fictive conservée : $File" }
    @{status='passed'; checks=$Checks.ToArray(); setup_sha256=$Manifest.msi_sha256; fictitious_data_only=$true; manual_GUI_DPI_and_drag_drop='still to perform'} | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 (Join-Path $Resultats 'resultat_installation_R9.json')
} catch {
    @{status='failed'; error=$_.Exception.Message; checks=$Checks.ToArray()} | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 (Join-Path $Resultats 'resultat_installation_R9.json')
    throw
} finally {
    foreach ($Key in $OldEnvironment.Keys) { [Environment]::SetEnvironmentVariable($Key,$OldEnvironment[$Key],'Process') }
    # Never force-stop the application or uninstall while an owned test process is still alive.
    if ($Installed) { Write-Warning 'Installation de test conservée après échec ; fermer LBR puis désinstaller via Paramètres Windows. Journaux préservés.' }
    Stop-Transcript
}
