@echo off
setlocal
py -3 -B "%~dp0private_mode.py" --check
set "rc=%errorlevel%"
if "%rc%"=="3" echo BLOCKED esperado: falta adaptador real del host. No introducir secretos.
exit /b %rc%
