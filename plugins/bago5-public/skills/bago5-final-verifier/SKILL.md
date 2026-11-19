---
name: bago5-final-verifier
description: Revisa la candidata final contra los criterios de aceptación y emite una decisión de cierre con evidencias.
---

# Verificar una entrega

1. Confirma el identificador de candidata y los criterios obligatorios. Inspecciona el diff, dependencias y alcance real del encargo. Identifica si participaste en la implementación para declarar tu grado de independencia.

2. Reproduce los casos que acreditan el comportamiento pedido y las regresiones críticas. Comprueba qué datos proceden de la ejecución final y cuáles pertenecen a una versión anterior.

3. Por cada criterio registra entrada, esperado, observado y fuente. Separa PASS, FAIL, NOT_RUN e inconcluso. Un resumen del implementador orienta la revisión y requiere contraste con el artefacto.

## Criterio de cierre

Emite un dictamen acotado. Si un criterio obligatorio falla o falta su evidencia, mantén abierto el cierre e indica qué prueba lo resolvería. Distingue verificación técnica y aceptación por la persona usuaria.

Para un recorrido interactivo, comprueba la acción desde la entrada normal del usuario en el destino y la candidata solicitados, con su rol y datos autorizados. Distingue la vista de visitante, la identidad autenticada, la entrada al recurso correcto y las acciones consecutivas dentro del recurso. Cuando el encargo pida persistencia, observa el guardado y una relectura posterior desde el destino. Si la escritura queda fuera de lo autorizado, registra `NOT_RUN` y su causa. Si no se pidió persistencia, evalúa el recorrido de lectura por sí mismo.

Conserva un recibo por hito con resultado esperado y observado, referencia de evidencia, destino, candidata y rol efectivo. Vincula los hitos que deban funcionar seguidos a la misma ejecución del recorrido y en su orden real. Usa referencias sin secretos para el recurso y la ejecución. Una respuesta HTTP 200 o una vista estática pueden acreditar la entrega de esa página. Las pruebas locales, maquetas y simulaciones acreditan su respectivo contexto. La operación privada en producción exige observar su resultado en producción.

Si falta o falla un hito obligatorio, abre la respuesta con **PARCIAL** o **BLOQUEADO** y nombra la acción afectada. A continuación enumera qué sí se verificó, dónde y qué falta para resolverla. Para contrastar recibos aportados se puede utilizar el [comprobador de recorridos](scripts/assess_journey.py) con el [formato de criterios y recibos](references/journey.md). Su resultado evalúa la documentación de la prueba; contrasta las referencias con la evidencia real antes de dar el cierre.

