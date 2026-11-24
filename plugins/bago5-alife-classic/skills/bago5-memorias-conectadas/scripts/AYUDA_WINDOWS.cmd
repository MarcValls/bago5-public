@echo off
setlocal
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher no disponible. Instala Python 3.10+ antes de ejecutar el gestor local.
  pause
  exit /b 2
)
py -3 "%~dp0mv_hub.py" --help
pause
