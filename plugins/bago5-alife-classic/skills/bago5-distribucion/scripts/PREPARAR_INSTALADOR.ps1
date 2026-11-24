[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$SourceArchive)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$generator=Join-Path $root 'build_installer.py'
$source=(Resolve-Path -LiteralPath $SourceArchive).Path
$out=Join-Path (Split-Path -Parent $source) 'BAGO5_PAQUETE_INSTALABLE'
if (Test-Path -LiteralPath $out) { throw 'Directorio de salida existente: no sobrescribir. Mueva o renombre el directorio anterior.' }
python -B $generator --source $source --output $out
if ($LASTEXITCODE -ne 0) { throw 'Generacion/verificacion FALLIDA' }
Write-Host 'Instalador completo generado en:' $out
Write-Host 'Extraiga el ZIP, ejecute .\INSTALAR_BAGO5.ps1 -VerifyOnly, despues .\INSTALAR_BAGO5.ps1'
