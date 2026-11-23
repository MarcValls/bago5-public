---
name: bago5-integridad-evidencias
description: Vincular una afirmación con archivos de evidencia verificables.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](../bago5/references/controles-especialistas.md#efecto).

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

Aplicar [bago5](../bago5/SKILL.md), proyecto y permisos actuales. En GPT Classic sin ejecucion real, preparar handoff y marcar ejecucion NOT_RUN.

Motor incluido: [bago_evidence_guard.py](../../optional-runtime/evidence-guard/bago_evidence_guard.py). Leer [uso y contratos](../../optional-runtime/evidence-guard/00_LEER_PRIMERO.md). Requiere Python 3.10+ con biblioteca estandar y acceso real a los archivos. Usar --help para la sintaxis exacta. Operaciones: create-manifest, verify-manifest, verify-json, seal-json, check-text.

Resolver raiz autorizada, archivos, roles, JSON Pointers y destino antes de actuar. create-manifest y seal-json escriben salidas nuevas; verificacion no repara originales. Rechazar hashes mal formados, controles C0/DEL, vinculos incompletos o bytes distintos. --allow-unbound-claims significa cobertura parcial, nunca aceptacion completa. Los hashes prueban integridad de bytes, no ejecucion funcional, autoria, permisos ni cierre. Los ejemplos W12 y evidencias_locales incluidos son sinteticos/historicos, no evidencias del proyecto actual.

## Procedimientos según el encargo

Elige únicamente el procedimiento correspondiente al objeto y al resultado pedido.

- [Vincula conclusiones con evidencias y sus fuentes](../bago5-procedencia-evidencias/procedimiento.md).
- [Relaciona pasos, herramientas y acciones mediante trazas](../bago5-trazas-ejecucion/procedimiento.md).
