$ErrorActionPreference = 'Stop'
# Starts from the extracted package; no assumed user or ZIP path.
$DemoPath = Join-Path $PSScriptRoot 'scripts/demo.py'
if (Get-Command python -ErrorAction SilentlyContinue) {
    & python -B -I $DemoPath
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -B -I $DemoPath
} else {
    throw 'Se necesita Python 3.10 o superior. No se ha instalado ni activado nada.'
}
exit $LASTEXITCODE
