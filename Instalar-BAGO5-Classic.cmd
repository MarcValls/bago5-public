@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
title BAGO5 Classic 0.4.59 - Instalador de Codex
set "BAGO5_SELECTOR=bago5-governed-classic@bago5-public-tools"
set "BAGO5_SOURCE=MarcValls/bago5-public@v0.4.59"
set "PATH=%PATH%;%LOCALAPPDATA%\Microsoft\WinGet\Links;%ProgramFiles%\Git\cmd;%LOCALAPPDATA%\Programs\Git\cmd"
rem Git for Windows: enable long paths for this installer and its children only.
if defined GIT_CONFIG_PARAMETERS (
  set "GIT_CONFIG_PARAMETERS=%GIT_CONFIG_PARAMETERS% 'core.longpaths=true'"
) else (
  set "GIT_CONFIG_PARAMETERS='core.longpaths=true'"
)
set "MODE=asistido"
if /i "%~1"=="--solo-instalar" set "MODE=terminal"
if not "%~1"=="" if /i not "%~1"=="--solo-instalar" goto :uso

echo BAGO5 Classic 0.4.59 para Codex
echo Instalador r2: https://github.com/MarcValls/bago5-public/releases/tag/v0.4.59-r2
echo.
call :requisito git Git.Git
if errorlevel 1 goto :fallo
call :requisito codex OpenAI.Codex
if errorlevel 1 goto :fallo
set "BAGO5_CODEX="
for /f "usebackq delims=" %%X in (`powershell.exe -NoProfile -Command "$c = Get-Command codex.exe,codex.cmd -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1; if ($c) { [Console]::OutputEncoding = New-Object Text.UTF8Encoding($false); [Console]::WriteLine($c.Source) }"`) do set "BAGO5_CODEX=%%X"
if not defined BAGO5_CODEX goto :fallo
call "%BAGO5_CODEX%" --version
if errorlevel 1 goto :fallo
call "%BAGO5_CODEX%" plugin add --help >nul 2>&1
if errorlevel 1 goto :incompatible

call :python_opcional
if errorlevel 1 goto :fallo
if "%MODE%"=="terminal" goto :terminal
echo Elige la carpeta en la que quieres trabajar. Codex te pedira permiso
echo para registrar el catalogo publico e instalar Classic en tu perfil.
echo Despues de instalar, sal de Codex con /quit para abrir la sesion con Classic.
set "BAGO5_WORK="
for /f "usebackq delims=" %%D in (`powershell.exe -NoProfile -STA -Command "Add-Type -AssemblyName System.Windows.Forms; $d = New-Object System.Windows.Forms.FolderBrowserDialog; $d.Description = 'Carpeta de trabajo para BAGO5 Classic'; if ($d.ShowDialog() -eq 'OK') { [Console]::OutputEncoding = New-Object Text.UTF8Encoding($false); [Console]::WriteLine($d.SelectedPath) }"`) do set "BAGO5_WORK=%%D"
if not defined BAGO5_WORK goto :cancelado
pushd "%BAGO5_WORK%" || goto :fallo
set "GUIA=Guia de instalacion de BAGO5 Classic. Explica los cambios en mi perfil y pideme permiso antes de instalar. Espera mi respuesta."
set "GUIA=%GUIA% Si acepto, ejecuta en orden codex plugin marketplace add %BAGO5_SOURCE% y codex plugin add %BAGO5_SELECTOR%."
set "GUIA=%GUIA% Si el catalogo ya estaba registrado, comprueba que procede de https://github.com/MarcValls/bago5-public.git y usa codex plugin marketplace upgrade bago5-public-tools para actualizarlo antes de instalar. No reemplaces catalogos locales ni fijados por el usuario. Usa la aprobacion del host para red y escritura del perfil. Relee codex plugin list --marketplace bago5-public-tools --json y verifica Classic 0.4.59 habilitado."
set "GUIA=%GUIA% Respeta la cancelacion. No edites el proyecto ni conectes cuentas. Al acabar indicame que use /quit para volver al instalador."
call "%BAGO5_CODEX%" --sandbox read-only --ask-for-approval on-request "%GUIA%"
if errorlevel 1 goto :fallo
call :verificar
if errorlevel 1 goto :cancelado
choice /C SN /N /M "Abrir ahora tu carpeta en Codex con Classic [S/N]? "
if errorlevel 2 exit /b 0
if not errorlevel 1 exit /b 0
call "%BAGO5_CODEX%" --sandbox workspace-write --ask-for-approval on-request "Usa $bago5 para guiarme en este proyecto. Preguntame por donde quiero empezar."
exit /b %ERRORLEVEL%

:terminal
echo Se registrara el catalogo publico y se instalara Classic en tu perfil de Codex.
choice /C SN /N /M "Permitir instalacion [S/N]? "
if errorlevel 2 goto :cancelado
if not errorlevel 1 goto :cancelado
call "%BAGO5_CODEX%" plugin marketplace add %BAGO5_SOURCE%
if errorlevel 1 (
  call :actualizar_catalogo
  if errorlevel 1 goto :fallo
)
call :comprobar_oferta
if errorlevel 1 goto :fallo
call "%BAGO5_CODEX%" plugin add %BAGO5_SELECTOR%
if errorlevel 1 goto :fallo
call :verificar
if errorlevel 1 goto :fallo
echo Abre tu carpeta de trabajo e inicia codex para usar $bago5.
exit /b 0

:actualizar_catalogo
rem Only refresh the existing official Git source. A local catalog belongs to its owner.
powershell.exe -NoProfile -Command ^
  "$ErrorActionPreference = 'Stop'; $out = & $env:BAGO5_CODEX plugin list --marketplace bago5-public-tools --available --json; if ($LASTEXITCODE -ne 0) { exit 1 };" ^
  "$j = ConvertFrom-Json -InputObject ($out -join [Environment]::NewLine); $origin = @(@($j.installed) + @($j.available) | Where-Object { $_.marketplaceSource.sourceType -ceq 'git' -and $_.marketplaceSource.source -ceq 'https://github.com/MarcValls/bago5-public.git' }); if (!$origin.Count) { exit 1 }"
if errorlevel 1 exit /b 1
call "%BAGO5_CODEX%" plugin marketplace upgrade bago5-public-tools
exit /b %ERRORLEVEL%

:comprobar_oferta
powershell.exe -NoProfile -Command ^
  "$ErrorActionPreference = 'Stop'; $out = & $env:BAGO5_CODEX plugin list --marketplace bago5-public-tools --available --json; if ($LASTEXITCODE -ne 0) { exit 1 };" ^
  "$j = ConvertFrom-Json -InputObject ($out -join [Environment]::NewLine); $offered = @($j.installed) + @($j.available) | Where-Object { $_.pluginId -ceq $env:BAGO5_SELECTOR -and $_.version -ceq '0.4.59' -and $_.marketplaceSource.source -ceq 'https://github.com/MarcValls/bago5-public.git' }; if (!$offered) { Write-Host 'El catalogo no ofrece Classic 0.4.59. Comprueba si lo tienes fijado a otra etiqueta.'; exit 1 }"
exit /b %ERRORLEVEL%

:verificar
powershell.exe -NoProfile -Command ^
  "$ErrorActionPreference = 'Stop'; $cli = $env:BAGO5_CODEX;" ^
  "$out = & $cli plugin list --marketplace bago5-public-tools --json; if ($LASTEXITCODE -ne 0) { exit 1 };" ^
  "$entry = (ConvertFrom-Json -InputObject ($out -join [Environment]::NewLine)).installed | Where-Object { $_.pluginId -ceq $env:BAGO5_SELECTOR -and $_.marketplaceSource.sourceType -ceq 'git' -and $_.marketplaceSource.source -ceq 'https://github.com/MarcValls/bago5-public.git' -and $_.installed -and $_.enabled -and $_.version -ceq '0.4.59' };" ^
  "if (!$entry) { exit 1 }; Write-Host 'BAGO5 Classic 0.4.59 instalado y habilitado.'"
exit /b %ERRORLEVEL%

:python_opcional
where /Q py
if not errorlevel 1 (
  py -3 -I -B -c "import sys; sys.exit(sys.version_info[:2] < (3, 11))" >nul 2>&1
  if not errorlevel 1 exit /b 0
)
echo Los hooks y auxiliares locales de Classic usan Python 3.11 o posterior.
where /Q winget
if errorlevel 1 (
  echo Puedes instalar Python mas adelante y continuar ahora con las habilidades.
  exit /b 0
)
choice /C SN /N /M "Instalar Python 3.13 con WinGet para estas funciones [S/N]? "
if errorlevel 2 exit /b 0
if not errorlevel 1 exit /b 0
winget install --exact --id Python.Python.3.13 --source winget
if errorlevel 1 exit /b 1
echo Si py no aparece aun en PATH, abre una terminal nueva tras la instalacion.
exit /b 0

:requisito
where /Q "%~1"
if not errorlevel 1 exit /b 0
where /Q winget
if errorlevel 1 goto :falta
echo Falta %~1. WinGet puede instalar el paquete %~2.
choice /C SN /N /M "Permitir la instalacion de %~2 [S/N]? "
if errorlevel 2 exit /b 1
if not errorlevel 1 exit /b 1
winget install --exact --id %~2 --source winget
if errorlevel 1 exit /b 1
where /Q "%~1"
if not errorlevel 1 exit /b 0
echo Vuelve a abrir el instalador para cargar el PATH que acaba de actualizarse.
exit /b 1

:falta
echo Instala %~2 y vuelve a abrir este archivo. WinGet no esta disponible.
exit /b 1
:incompatible
echo Actualiza Codex CLI a una version que admita codex plugin add.
:fallo
echo La operacion no se ha podido completar. Revisa el mensaje anterior.
if "%MODE%"=="asistido" pause
exit /b 1
:cancelado
echo Instalacion cancelada o sesion cerrada sin completar la instalacion.
exit /b 2
:uso
echo Uso: Instalar-BAGO5-Classic.cmd [--solo-instalar]
exit /b 1
