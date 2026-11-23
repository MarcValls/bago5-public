@echo off
setlocal DisableDelayedExpansion
where py >nul 2>nul
if not errorlevel 1 goto USE_PY
where python >nul 2>nul
if not errorlevel 1 goto USE_PYTHON
echo ERROR: Python 3 no encontrado. 1>&2
exit /b 9009

:USE_PY
py -3 -B "%~dp0rc4-goals\dispatch_prompt.py"
exit /b %ERRORLEVEL%

:USE_PYTHON
call python -B "%~dp0rc4-goals\dispatch_prompt.py"
exit /b %ERRORLEVEL%
