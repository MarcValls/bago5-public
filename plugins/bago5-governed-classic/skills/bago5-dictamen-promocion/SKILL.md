---
name: bago5-dictamen-promocion
description: Decidir si una candidata puede promoverse al destino.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](../bago5/references/controles-especialistas.md#efecto).

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# #BAGO5-promotion · Condiciones de aceptación

La promoción necesita candidata identificada, destino, cobertura, fuentes, resultados de pruebas, límites de independencia, riesgos y aceptación. Comprueba `STOP`, permisos y actividad antes de operar.

No declarar `GO` sobre evidencias sintéticas, hashes, informes de tests que no se ejecutaron o ausencia de fuentes. Exigir comprobación diferencial preservando capacidades, estado y antecedentes. Si la evidencia obligatoria no existe: `NO_GO` o `BLOQUEADO`, con motivo.

Un dictamen `GO` es una evaluación; publicar, desplegar, compartir, sustituir fuente, instalar o reanudar exige autorización/operación aparte. Verificar el destino después de cualquier publicación autorizada.

Vincula la promoción funcional al [recorrido de usuario en destino](../bago5-verificacion-cierre/references/recorrido-en-destino.md). Registra por separado la transferencia del paquete y el funcionamiento del recorrido solicitado.
