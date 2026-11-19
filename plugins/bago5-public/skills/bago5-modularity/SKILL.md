---
name: bago5-modularity
description: "Revisar límites de módulos, dependencias y duplicación de comportamiento antes de refactorizar."
---

# Auditar la modularidad

Sigue una operación real desde su punto de entrada hasta sus efectos. Lista módulos responsables, dependencias de entrada y salida, datos compartidos y callers. Distingue repetición de sintaxis de duplicación de una misma regla.

Para cada cambio propuesto identifica qué módulo será dueño de la regla, qué contrato seguirán usando los demás y cómo se conservarán compatibilidad, errores y orden de efectos. Prioriza los límites con responsabilidades mezcladas o dependencias cíclicas comprobadas.

Si el encargo incluye implementación, extrae una responsabilidad a la vez y mantiene los puntos de entrada existentes. Comprueba al menos dos consumidores cuando compartan la regla. Entrega mapa antes/después, ejemplo que evidencie la mejora, resultado de regresiones y dependencias pendientes.
