@echo off
setlocal DisableDelayedExpansion
pushd "%~dp0" || exit /b 2
where py >nul 2>nul
if not errorlevel 1 goto WITH_PY
where python >nul 2>nul
if not errorlevel 1 goto WITH_PYTHON
echo [FAIL] No se encontro Python 3 (py o python).
set "RET=9009"
goto END
:WITH_PY
py -3 -B tests\demo_local.py
set "RET=%ERRORLEVEL%"
goto END
:WITH_PYTHON
python -B tests\demo_local.py
set "RET=%ERRORLEVEL%"
:END
echo.
echo Resultado del lanzador: %RET%
pause
popd
exit /b %RET%
