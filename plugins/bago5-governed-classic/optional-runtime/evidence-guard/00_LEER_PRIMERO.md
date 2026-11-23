# BAGO Evidence Guard v1.0.0

## Objetivo y alcance

Evitar que los informes de evidencia contengan hashes SHA-256 copiados incorrectamente, declaraciones no contrastadas con los archivos de origen o caracteres C0/DEL prohibidos. Caso motivador: W12 r1 (dos digests de 65 caracteres) y r3 (controles en Markdown).

**Es una herramienta independiente y genérica.** No instala nada en BAGO5os, no cambia RC4, no sustituye los contratos de GOALS, TaskStore, Relay o STOP, y no cierra W12. Solo genera o verifica artefactos de integridad. Python 3.10+; biblioteca estándar, sin dependencias externas.

## Pruebas rápidas de doble clic, en Windows

1. Descomprimir el ZIP en una carpeta de trabajo **sin sustituir ninguna instalación existente**.
2. Ejecutar `01_EJECUTAR_PRUEBAS.cmd`: pruebas de contrato y regresión, incluidos los dos errores de 65 caracteres.
3. Ejecutar `02_DEMO_SINTETICA.cmd`: reproduce los errores r1/r3 en datos sintéticos, crea evidencia válida nueva y comprueba que los originales no se alteran.

Los lanzadores no instalan nada, no utilizan red y usan `py -3` o `python`. El resultado debe ser **24 tests PASS**; la demo informa `r1=FAIL esperado`, `r3=FAIL esperado`, `nuevo JSON=PASS`, `manifiesto=PASS`. El FAIL esperado en un caso negativo **no es** un fallo de la demo.

## Uso en un proyecto real (PowerShell o terminal)

> Sustituye los nombres por las rutas reales. No se presupone que este entorno tenga acceso al disco de Windows.

### A. Generar un inventario SHA-256 nuevo, sin plantilla

Crear un archivo de configuración como `examples/inventario.json`, que enumere **todos** los archivos que se quieran acreditar con rutas relativas a la raíz elegida. Ejemplo:

```json
{
  "schema": "bago.evidence.guard.spec.v1",
  "files": [
    {"path": "frontend/src/ExternalConnections.css", "role": "source"},
    {"path": "evidence/logs/test-pass.txt", "role": "log"}
  ]
}
```

Ejecutar:

```powershell
py -3 -B .\bago_evidence_guard.py create-manifest --root "C:\RUTA\PROYECTO" --spec ".\inventario.json" --out-dir "C:\RUTA\REVISION\integridad-r5" --label "REVISION_W12_R5"
py -3 -B .\bago_evidence_guard.py verify-manifest --root "C:\RUTA\PROYECTO" --manifest "C:\RUTA\REVISION\integridad-r5\manifest.json" --markdown "C:\RUTA\REVISION\integridad-r5\informe.md"
```

Se crean `manifest.json` e `informe.md` **en una carpeta nueva**. No sobreescribe carpetas de revisión existentes. `verify-manifest` recalcula todos los hashes y compara también el Markdown byte a byte con la representación derivada del manifiesto.

### B. Comprobar los hashes dentro de un JSON existente (por ejemplo W12 r4)

Crear `vinculos.json` (ver `examples/vinculos.json`). Cada entrada relaciona un campo JSON concreto (JSON Pointer) con el **archivo real** al que atribuye un hash. La herramienta no adivina esa relación.

```json
{
  "schema": "bago.evidence.guard.bindings.v1",
  "expected_count": 2,
  "bindings": [
    {"pointer": "/sources/css/sha256", "path": "frontend/src/ExternalConnections.css"},
    {"pointer": "/logs/0/sha256", "path": "evidence/logs/test-fail.txt"}
  ]
}
```

**Para W12 con 15 declaraciones, usar `expected_count: 15` y enumerar los 15 campos y archivos exactos.** La estructura anterior es solo un ejemplo de dos campos. Las rutas en el informe real pueden ser otras; consultar su estructura antes de configurar los vínculos.

```powershell
py -3 -B .\bago_evidence_guard.py verify-json --root "C:\RUTA\PROYECTO" --report "C:\RUTA\W12-independent-review-r4.json" --bindings "C:\RUTA\vinculos_W12.json" --expected-count 15 --text "C:\RUTA\W12-independent-review-r4.md"
```

`verify-json` no modifica el JSON auditado. Rechaza hashes de 63/65 caracteres, valores hexadecimales inválidos y hashes de 64 caracteres que no coincidan con los bytes actuales. Si un hash tiene 65 caracteres y al quitar uno coincide, muestra posiciones/carácter como **diagnóstico**, pero **nunca corrige ni acepta automáticamente** ese valor.

De forma predeterminada, también rechaza campos de hash sin correspondencia explícita (`UNBOUND_HASH_CLAIMS`). Si existen campos que **no representan archivos**, deben separarse en un contrato explícito; `--allow-unbound-claims` permite una revisión parcial, **no** una aceptación integral.

### C. Generar un JSON nuevo con la misma estructura del informe existente

Usar `seal-json` para una plantilla que contenga `"__SHA256__"` en los campos que deben rellenarse. Las rutas y JSON Pointers se declaran en `vinculos.json`. El destino **debe ser nuevo**; nunca se modifica la plantilla ni W12 r1–r4.

```powershell
py -3 -B .\bago_evidence_guard.py seal-json --root "C:\RUTA\PROYECTO" --template "C:\RUTA\W12_TEMPLATE.json" --bindings "C:\RUTA\vinculos_W12.json" --out "C:\RUTA\W12_R5_NUEVO.json" --expected-count 15
```

El script calcula cada SHA-256 desde los archivos, lo introduce **en memoria**, serializa el JSON, lo vuelve a leer y recalcula los 15 hashes sobre los bytes identificados. No pasa los digests por la generación de texto de un modelo.

### D. Validar caracteres de control aunque no existan hashes

```powershell
py -3 -B .\bago_evidence_guard.py check-text --file "C:\RUTA\W12_R4.json" --file "C:\RUTA\W12_R4.md"
```

Valida UTF-8, claves JSON repetidas y C0/DEL prohibidos en el contenido. Se permiten únicamente tabulador, retorno de carro y salto de línea como separadores de texto; los demás controles C0 y DEL se rechazan. Los archivos de datos **no** se interpretan como texto al calcular su hash (pueden ser binarios).

## Condición de aceptación para Codex

Para cada informe W12 futuro:

1. Fijar identidad de la candidata, ubicación de los archivos y **lista exhaustiva** de las declaraciones de integridad (`expected_count`).
2. Calcular y serializar los SHA-256 **mediante el script**, sin transcribirlos desde la conversación ni crearlos con plantillas de texto generativo.
3. Ejecutar `verify-json` después de escribir y `check-text` para los documentos Markdown/JSON entregados; ambos deben devolver **código 0**.
4. Si aparece discrepancia, mantener r1–r4 y la candidata intactos, registrar FAIL y no aceptar ni cerrar W12 por inferencia. Crear una revisión nueva solo tras localizar el problema.
5. Respetar STOP, autorización y el alcance existente. El script no concede permisos ni reanuda procesos.

## Límites honestos

- El SHA-256 verifica **identidad de bytes**; no certifica quién produjo el archivo, la veracidad del contenido, una firma criptográfica, la calidad del producto ni una ejecución funcional.
- Una prueba PASS sobre los archivos **actuales** no valida automáticamente snapshots históricos con otros bytes.
- Si un archivo cambia durante la lectura, se intenta detectar el cambio comparando metadatos antes y después. Sin snapshots atómicos del sistema de archivos no puede garantizarse consistencia frente a adversarios concurrentes que manipulen metadatos.
- La cobertura completa de un JSON ajeno depende de que `vinculos.json` enumere todas las declaraciones que interesan. `expected_count` evita aceptar accidentalmente dos campos cuando se esperan quince, pero no descubre campos semánticos ocultos.
- No se ha ejecutado en tu Windows ni sobre W12 r4 real desde este entorno. Las pruebas incluidas se han ejecutado en Linux/Python 3.13.5; Windows está NOT_RUN.

**Dictamen de este componente:** IMPLEMENTADO; pruebas sintéticas locales superadas; validación W12 real e integración con la Suite pendientes.
