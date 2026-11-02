$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Sonde réservée au runner CI.' }
$Log=Join-Path $env:GITHUB_WORKSPACE '.ci-logs'
New-Item -ItemType Directory -Path $Log -Force | Out-Null
$Roots=@("${env:ProgramFiles(x86)}\Windows Kits","${env:ProgramFiles(x86)}\WiX Toolset v3.14\bin")
if ($env:WIX) { $Roots+=Join-Path $env:WIX 'bin' }
$Found=@(foreach ($Root in ($Roots | Select-Object -Unique)) {
  if (Test-Path -LiteralPath $Root) {
    Get-ChildItem -LiteralPath $Root -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -in @('msival2.exe','darice.cub','smoke.exe','evalcom2.dll') } | ForEach-Object {
      [pscustomobject]@{path=$_.FullName;name=$_.Name;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash;version=$_.VersionInfo.FileVersion}
    }
  }
})
@{tools=$Found;ICE_validation_executed=$false;note='Inventaire uniquement. WiX 3 smoke supprime ICE33 et ICE66 par défaut : ne pas le présenter comme une validation ICE exhaustive.'} | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 (Join-Path $Log 'outillage_ICE.json')
