@echo off
setlocal
pushd "%~dp0.." || exit /b 2
py -3 -B -m unittest discover -s tests -v
set "rc=%errorlevel%"
popd
if not "%rc%"=="0" echo NO_GO: revisar errores y pruebas omitidas. No usar secretos reales.
if "%rc%"=="0" echo Pruebas terminadas. Revisar omisiones. Host real y KeePassXC: NOT_RUN.
exit /b %rc%
