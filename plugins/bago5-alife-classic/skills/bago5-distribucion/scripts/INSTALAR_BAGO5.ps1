# BAGO5 local installer, launched explicitly after inspection.
[CmdletBinding(SupportsShouldProcess=$true)]
param([switch]$VerifyOnly, [switch]$NoOnboarding)
$ErrorActionPreference = 'Stop'
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $dir 'plugin'
$manifestFile = Join-Path $dir 'manifest.sha256.json'
if (!(Test-Path -LiteralPath $source -PathType Container) -or !(Test-Path -LiteralPath $manifestFile -PathType Leaf)) { throw 'El paquete NO contiene el plugin completo y su manifiesto. No instalar.' }
$spec = Get-Content -LiteralPath $manifestFile -Raw -Encoding UTF8 | ConvertFrom-Json
$plugin = Get-Content -LiteralPath (Join-Path $source 'plugin.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$codex = Get-Content -LiteralPath (Join-Path $source '.codex-plugin/plugin.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($spec.schema -ne 'bago5-distribution.v1' -or $plugin.name -ne 'bago5-governed-classic' -or $codex.name -ne $plugin.name -or $codex.version -ne $plugin.version -or $spec.version -ne $plugin.version) { throw 'Identidad o versión de plugin no coincide' }
$names = @($spec.files.PSObject.Properties.Name)
if ($names.Count -ne [int]$spec.file_count -or $names.Count -lt 20) { throw 'Inventario incompleto' }
$unsafe = @(Get-ChildItem -LiteralPath $source -Recurse -Force -Attributes ReparsePoint)
if ($unsafe.Count -gt 0) { throw 'El paquete contiene enlaces o reparse points no permitidos' }
$physical = @(Get-ChildItem -LiteralPath $source -Recurse -File -Force)
if ($physical.Count -ne $names.Count) { throw 'Inventario de archivos diferente al manifiesto' }
foreach ($name in $names) {
  if ($name -match '(^|/|\\)\.\.($|/|\\)' -or [IO.Path]::IsPathRooted($name)) { throw 'Ruta insegura en inventario' }
  $path = Join-Path $source ($name -replace '/', [IO.Path]::DirectorySeparatorChar)
  if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw "Falta: $name" }
  $item=Get-Item -LiteralPath $path -Force
  if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Enlace o junction no permitido: $name" }
  $actual=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($actual -ne [string]$spec.files.PSObject.Properties[$name].Value) { throw "Hash incorrecto: $name" }
}
Write-Host "Integridad PASS: $($plugin.name) $($plugin.version), $($names.Count) archivos"
if ($VerifyOnly) { exit 0 }
$base=Join-Path $HOME '.agents\plugins\plugins'
$destination=Join-Path $base $plugin.name
$catalogue=Join-Path $HOME '.agents\plugins\marketplace.json'
$marketRoot=Split-Path -Parent $catalogue
$settingsRoot=Join-Path $marketRoot 'bago5'
$alifeConfig=Join-Path $settingsRoot 'alife-marketplace.json'
$onboardingPreference=Join-Path $settingsRoot 'onboarding.json'
$activation='https://alifememories.com/memoria-viva'
$expectedAlife=[ordered]@{
 schema='bago5.alife-marketplace.v1'
 canonical_origin='https://alifememories.com'
 catalog_url='https://alifememories.com/api/templates'
 compatibility_url='https://alifememories.com/api/templates/compatibility'
 activation_url=$activation
}
# Check existing configuration before the first write. Different endpoints are
# preserved and reported, never silently replaced.
$writeAlife=!(Test-Path -LiteralPath $alifeConfig)
if (!$writeAlife) {
 $oldAlife=Get-Content -LiteralPath $alifeConfig -Raw -Encoding UTF8 | ConvertFrom-Json
 $same=@($oldAlife.PSObject.Properties.Name).Count -eq $expectedAlife.Count
 foreach ($key in $expectedAlife.Keys) {
  if ([string]$oldAlife.PSObject.Properties[$key].Value -cne [string]$expectedAlife[$key]) { $same=$false }
 }
 if (!$same) { throw 'Configuracion ALIFE diferente: se conserva. Revise el destino antes de instalar.' }
}
$market= if (Test-Path -LiteralPath $catalogue) { Get-Content -LiteralPath $catalogue -Raw -Encoding UTF8 | ConvertFrom-Json } else { [pscustomobject]@{ name='bago5-personal'; plugins=@() } }
if (!$market.name) { throw 'El marketplace nativo existente no tiene identidad; no se sustituye.' }
if (!$market.PSObject.Properties['plugins']) { $market | Add-Member -NotePropertyName plugins -NotePropertyValue @() }
$rel='./plugins/'+$plugin.name
$entry=[pscustomobject]@{ name=$plugin.name; source=[pscustomobject]@{ source='local'; path=$rel }; policy=[pscustomobject]@{ installation='AVAILABLE'; authentication='ON_INSTALL' }; category='Developer Tools' }
$others=@($market.plugins | Where-Object {$_.name -ne $plugin.name})
$market.plugins=@($others)+@($entry)
if (!$PSCmdlet.ShouldProcess($destination,'Instalar BAGO5, conservar copias y registrar sus catalogos')) { return }
if (!(Test-Path -LiteralPath $base)) { New-Item -ItemType Directory -Path $base -Force | Out-Null }
$stamp=[DateTime]::UtcNow.ToString('yyyyMMddHHmmssfff')+'.'+[Guid]::NewGuid().ToString('N')
$backup=Join-Path $base ($plugin.name+'.backup.'+$stamp)
$catalogueBackup=$catalogue+'.backup.'+$stamp
$hadDestination=Test-Path -LiteralPath $destination
$hadCatalogue=Test-Path -LiteralPath $catalogue
if ($hadDestination) { Move-Item -LiteralPath $destination -Destination $backup }
try {
 Copy-Item -LiteralPath $source -Destination $destination -Recurse -Force
 if (!(Test-Path -LiteralPath $settingsRoot)) { New-Item -ItemType Directory -Path $settingsRoot -Force | Out-Null }
 if ($hadCatalogue) { Copy-Item -LiteralPath $catalogue -Destination $catalogueBackup }
 $tmp=$catalogue+'.tmp.'+$stamp
 $market | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath $tmp -Encoding UTF8
 Move-Item -LiteralPath $tmp -Destination $catalogue -Force
 if ($writeAlife) {
  $tmpAlife=$alifeConfig+'.tmp.'+$stamp
  $expectedAlife | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $tmpAlife -Encoding UTF8
  Move-Item -LiteralPath $tmpAlife -Destination $alifeConfig
 }
} catch {
 if (Test-Path -LiteralPath $destination) { Remove-Item -LiteralPath $destination -Recurse -Force }
 if ($hadDestination -and (Test-Path -LiteralPath $backup)) { Move-Item -LiteralPath $backup -Destination $destination }
 if ($hadCatalogue -and (Test-Path -LiteralPath $catalogueBackup)) { Copy-Item -LiteralPath $catalogueBackup -Destination $catalogue -Force }
 elseif (!$hadCatalogue -and (Test-Path -LiteralPath $catalogue)) { Remove-Item -LiteralPath $catalogue }
 throw
}
Write-Host 'BAGO5 instalado en el directorio local. Catalogos configurados; conexion ALIFE y carga del host NO COMPROBADAS.'
Write-Host 'Compruebe con la interfaz del host o sus comandos disponibles: codex plugin marketplace list; codex plugin list'
Write-Host 'El catalogo ALIFE no instala versiones candidatas ni concede permisos.'
# Do not manufacture a host installation hook. This offer runs only in this
# explicitly launched installer; all other hosts use first invocation.
if ($NoOnboarding) {
 Write-Host 'Incorporacion omitida. Cuando quiera activar su memoria:' $activation
 return
}
$interactive=[Environment]::UserInteractive
try { if ([Console]::IsInputRedirected) { $interactive=$false } } catch { $interactive=$false }
if (!$interactive) {
 Write-Host 'Sin entrada interactiva. BAGO5 ofrecera crear/conectar memoria en su primera invocacion:' $activation
 return
}
Write-Host ''
Write-Host 'Quieres crear una memoria personal en alifememories.com?'
Write-Host '1. Crear mi memoria: Abre Mi espacio en ALIFE y crea tu memoria privada.'
Write-Host '2. Conectar una memoria existente.'
Write-Host '3. Continuar sin memoria.'
$choice=Read-Host 'Elige 1, 2 o 3 (Enter: continuar sin memoria)'
if ($choice -notin @('1','2','3','')) { Write-Host 'Eleccion no reconocida. No se inicia el alta.'; return }
$selected=if ($choice -eq '1') { 'create_alife_memory' } elseif ($choice -eq '2') { 'connect_existing' } else { 'continue_without_memory' }
$preference=[ordered]@{ schema='bago5.onboarding-preference.v1'; choice=$selected; server_state='UNVERIFIED'; source='explicit_local_installer_choice'; saved_at=[DateTime]::UtcNow.ToString('o') }
if (Test-Path -LiteralPath $onboardingPreference) { Copy-Item -LiteralPath $onboardingPreference -Destination ($onboardingPreference+'.backup.'+$stamp) }
$preference | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $onboardingPreference -Encoding UTF8
if ($choice -in @('1','2')) {
 Write-Host 'Se abrira ALIFE. Si ALIFE solicita acceso, completa el inicio de sesion en el portal.'
 if ($choice -eq '2') { Write-Host 'En ALIFE elige la memoria existente; no crees otra para resolver la conexion.' }
 try { Start-Process -FilePath $activation }
 catch { Write-Host 'No se pudo abrir el navegador. Abre esta direccion:' $activation }
 Write-Host 'Abrir la pagina no confirma correo, memoria, OAuth ni conexion. BAGO5 comprobara esos pasos por separado.'
} else {
 Write-Host 'Continuas sin memoria. No se ha enviado correo ni creado espacio.'
}
