---
name: bago5-integridad-evidencias
description: Registrar afirmaciones, comprobaciones y sus relaciones con fuentes, recuerdos, objetivos y artefactos.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](../bago5/references/controles-especialistas.md#efecto).

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

Aplicar [bago5](../bago5/SKILL.md), proyecto y permisos actuales. Cuando la comprobación requiera una capacidad de ejecución no disponible, conservar el trabajo realizable con las herramientas presentes y marcar solo la comprobación pendiente como NOT_RUN. El nombre del anfitrión no determina sus capacidades.

Motor incluido: bago_evidence_guard.py (motor local independiente). Leer [uso y contratos](../bago5/references/local/evidence-guard/00_LEER_PRIMERO.md). Requiere Python 3.10+ con biblioteca estandar y acceso real a los archivos. Usar --help para la sintaxis exacta. Operaciones: create-manifest, verify-manifest, verify-json, seal-json, check-text.

Resolver raiz autorizada, archivos, roles, JSON Pointers y destino antes de actuar. create-manifest y seal-json escriben salidas nuevas; verificacion no repara originales. Rechazar hashes mal formados, controles C0/DEL, vinculos incompletos o bytes distintos. --allow-unbound-claims significa cobertura parcial, nunca aceptacion completa. Los hashes prueban integridad de bytes, no ejecucion funcional, autoria, permisos ni cierre. Los ejemplos W12 y evidencias_locales incluidos son sinteticos/historicos, no evidencias del proyecto actual.

## Evidencias en ALIFE

Aplica [el contrato de interacción y evidencias](../bago5/references/workspace-evidence.md). La evidencia puede vincularse a recuerdos, objetivos, artefactos y relaciones por referencias completas; un archivo es una posible fuente. Registra por separado afirmación, método, acción, entorno real o simulado, resultado, fuentes y revisión. Una ficha guardada, un vínculo o un hash no acreditan veracidad, ejecución ni aceptación. Si el servicio solo ofrece recuerdos nativos, usa únicamente su contrato anunciado; no inventes campos o endpoints de evidencia. Una interfaz candidata y una capacidad desplegada se informan por separado.

## Procedimientos según el encargo

Elige únicamente el procedimiento correspondiente al objeto y al resultado pedido.

- [Vincula conclusiones con evidencias y sus fuentes](../bago5-procedencia-evidencias/procedimiento.md).
- [Relaciona pasos, herramientas y acciones mediante trazas](../bago5-trazas-ejecucion/procedimiento.md).

En Codex, aplica el [formato de respuesta de BAGO](../bago5/SKILL.md#respuestas-en-codex) al comunicar el resultado.

