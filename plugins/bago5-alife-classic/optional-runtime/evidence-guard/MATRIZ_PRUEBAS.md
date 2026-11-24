# Matriz de pruebas — BAGO Evidence Guard v1.0.0

| Grupo | Escenarios | Aceptación |
|---|---|---|
| Generación | Sellar JSON desde plantilla, verificar y no sobrescribir | JSON nuevo consistente; fuente y plantilla intactas |
| Inserciones r1 | Añadir `d` tras posición 25 y `1` tras posición 11 | Rechazo `INVALID_SHA256_FORMAT` y diagnóstico de inserción; sin autocorrección |
| Integridad material | SHA-256 de 64 caracteres distinto y archivo modificado después de guardar recibo | Rechazo `DIGEST_MISMATCH` |
| Texto r3 | Markdown con ESC/NUL, JSON con control escapado | Rechazo `FORBIDDEN_C0_DEL` |
| Estructura | Claves JSON duplicadas, `NaN`, campo SHA no vinculado, SHA numérico | Rechazo conservador |
| Rutas | `../`, rutas absolutas, segmentos ambiguos, enlaces simbólicos a archivo/directorio | Rechazo; sin abandonar la raíz |
| Cobertura | Se exigen 15 vínculos y solo se declaran 2 | Rechazo antes de afirmar PASS |
| Manifiesto | Generar y verificar 15 fuentes sintéticas | 15/15; mismo contenido de manifiesto/Markdown |
| Manipulación posterior | Alterar manifiesto, tamaño o Markdown | Rechazo material/estructural |
| Binarios | Hash de bytes con NUL y caracteres no textuales | SHA-256 correcto sin imponer decodificación |

**Ejecución local:** 24 tests unitarios + 1 demostración orquestada con dos negativos esperados y dos positivos.

**No ejecutado aquí:** Windows real, ubicaciones originales de W12 r1–r4, integración con TaskStore/RC4, escenarios físicos de corte de luz. No declarar estos apartados PASS hasta reproducirlos.
