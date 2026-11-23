@echo off
setlocal DisableDelayedExpansion
set "BASE=%~dp0"
if not "%~1"=="" goto RESOLVE
set /p "WORKSPACE=Carpeta del proyecto (ruta completa): "
if "%WORKSPACE%"=="" exit /b 3
set "INTERACTIVE=1"
:RESOLVE
where py >nul 2>nul
if not errorlevel 1 goto USE_PY
where python >nul 2>nul
if not errorlevel 1 goto USE_PYTHON
echo ERROR: Python 3 no encontrado.
exit /b 9009
:USE_PY
if defined INTERACTIVE goto USE_PY_INTERACTIVE
py -3 -B "%BASE%goal_bridge.py" %*
set "RESULT=%ERRORLEVEL%"
goto END
:USE_PY_INTERACTIVE
py -3 -B "%BASE%goal_bridge.py" --workspace "%WORKSPACE%" resume
set "RESULT=%ERRORLEVEL%"
goto END
:USE_PYTHON
if defined INTERACTIVE goto USE_PYTHON_INTERACTIVE
python -B "%BASE%goal_bridge.py" %*
set "RESULT=%ERRORLEVEL%"
goto END
:USE_PYTHON_INTERACTIVE
python -B "%BASE%goal_bridge.py" --workspace "%WORKSPACE%" resume
set "RESULT=%ERRORLEVEL%"
:END
if defined INTERACTIVE pause
exit /b %RESULT%
