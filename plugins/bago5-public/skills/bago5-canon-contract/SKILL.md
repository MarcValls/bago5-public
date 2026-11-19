---
name: bago5-canon-contract
description: Compara un contrato versionado con su implementación y clasifica las cláusulas demostradas y pendientes.
---

# Contrastar un contrato canónico

1. Localiza fuente normativa, versión, alcance y huella. Identifica por separado los fuentes del proyecto, la distribución instalada, el entorno de ejecución y su estado mutable.

2. Descompón cada cláusula obligatoria en condición previa, entrada, salida y regla de rechazo. Enlaza cada condición con la implementación y al menos un vector que discrimine cumplimiento e incumplimiento.

3. Ejecuta los vectores contra la candidata exacta. Si la prueba escribe estado usa un espacio de prueba autorizado. Ante una discrepancia entre revisiones explica cuál gobierna esa candidata y conserva ambas referencias.

## Criterio de cierre

Entrega una matriz de cláusulas con veredicto y evidencia. Si queda una condición obligatoria sin cobertura, delimita el cumplimiento parcial e identifica la comprobación precisa que falta.

