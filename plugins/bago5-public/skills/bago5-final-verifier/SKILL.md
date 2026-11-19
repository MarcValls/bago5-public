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

