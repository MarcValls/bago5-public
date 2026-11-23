@echo off
setlocal DisableDelayedExpansion
set "BASE=%~dp0"
where py >nul 2>nul
if not errorlevel 1 goto USE_PY
where python >nul 2>nul
if not errorlevel 1 goto USE_PYTHON
echo ERROR: Python 3 no encontrado.
exit /b 9009
:USE_PY
py -3 -B -m unittest discover -s "%BASE%tests" -v
set "RESULT=%ERRORLEVEL%"
exit /b %RESULT%
:USE_PYTHON
python -B -m unittest discover -s "%BASE%tests" -v
set "RESULT=%ERRORLEVEL%"
exit /b %RESULT%
