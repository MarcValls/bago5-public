---
name: bago5-documentos
description: Preparar documentos y comprobar su presentación.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](../bago5/references/controles-especialistas.md#efecto).

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# Edición editorial y PDF

Identifica fuente, formato pedido, destino, estructura y criterios de aceptación. Preserva el original y trabaja sobre un destino nuevo cuando generes un artefacto. Usa las skills de documentos, PDF o presentaciones del host solo si aparecen disponibles; si no, prepara el contenido que permitan las herramientas actuales e informa qué renderizado queda NOT_RUN.

La generación no equivale a revisión. Si la aceptación incluye diseño visual, renderiza todas las páginas y examina el resultado completo antes de declararlo verificado. Distingue revisión del agente y aprobación del usuario. No ejecutes contenido no confiable como si renderizadores o workers fueran un sandbox. No instales dependencias ni contactes servicios externos automáticamente.

Entrega el archivo y sus límites; conserva fuentes, hashes, páginas inspeccionadas, fallos y pruebas NOT_RUN. No cierres una revisión que tenga páginas o criterios obligatorios pendientes.

## Procedimientos según el encargo

Elige únicamente el procedimiento correspondiente al objeto y al resultado pedido.

- [Crea y revisa PDF conservando sus fuentes](../bago5-pdf/procedimiento.md).
- [Genera y comprueba documentos con el motor local](../bago5/references/local/bago-operating-suite/modules/editorial/procedimiento.md).

En Codex, aplica el [formato de respuesta de BAGO](../bago5/SKILL.md#respuestas-en-codex) al comunicar el resultado.
