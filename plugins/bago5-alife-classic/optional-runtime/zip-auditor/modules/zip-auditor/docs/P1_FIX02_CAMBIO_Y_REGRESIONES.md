# ZIP Auditor — P1 FIX02

Tipo: derivada aislada sobre ZIPA-INTEGRATION-01; no reescribe la Suite RC2 original.

## Incidente

Dos ZIP con README.md y package.json distintos, sin bytes ni módulos comunes, eran propuestos como candidatos a fusionar por coincidencia accidental de rutas.

## Cambio

Se suprime SOLO la candidatura cuando todas las rutas compartidas son nombres genéricos de primer nivel, sus hashes difieren, no hay ningún hash de contenido compartido y los inventarios están completos. Se registra el contador de pares descartados. Se conserva la opción de distribuir ZIP intactos.

## Invariantes

- Sin mezcla, extracción ni ejecución de los archivos ZIP inspeccionados.
- Inventarios incompletos: no se ocultan alertas.
- Conflictos en código no genérico: se mantienen.
- Casos de bytes idénticos y de contenido compartido: se mantienen.
- Las propuestas no son autorizaciones de escritura.
- Windows real requiere prueba del EXE antes de promoción.

## Pruebas positivas/negativas

`control/tests/test_fusion_analysis.py` incluye cuatro regresiones: nombres genéricos, código real, incompleto y diferencia de mayúsculas. Ver evidencia en el pack externo.
