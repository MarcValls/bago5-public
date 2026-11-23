---
name: bago5-interfaces
description: Diseñar e implementar interfaces utilizables.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](../bago5/references/controles-especialistas.md#efecto).

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# UI y frontend con alcance comprobable

Inspecciona la interfaz y el código actuales antes de proponer cambios. Identifica navegación, estado, APIs reales, errores/vacíos/carga, accesibilidad y criterios visuales del proyecto. Distingue una maqueta o preview desconectada de la aplicación que usa la persona.

Para implementación, conserva el stack y los contratos existentes; coordina cambios de aplicación con bago5-aplicaciones-juegos y cambios generales de código con bago5-desarrollo. Usa el skill frontend disponible en el host si está realmente expuesto. Respeta los criterios de plataforma del proyecto y no infieras que debe probarse móvil o desktop.

Verifica la interfaz ejecutada con browser/UI real solo si esa capacidad está disponible y el usuario pidió comprobarla. Un build, preview, screenshot o inspección de fuente prueba únicamente su alcance. Si no hay acceso al host de UI, entrega análisis/cambio de fuente y marca la revisión visual NOT_RUN.

Para auditoria estatica JSX/JS/CSS, usar [bago5-interfaz-react](../bago5-interfaz-react/procedimiento.md) (BAGO5-UI-AUDIT); sus heuristicas no sustituyen pruebas del navegador.

Aplicar el [contrato de cambios y matriz de evidencia](references/change-contract.md) para cambios materiales y trazas UI/backend.

## Procedimientos según el encargo

Elige únicamente el procedimiento correspondiente al objeto y al resultado pedido.

- [Implementa interfaces de inspección de decisiones](../bago5-interfaz-decisiones/procedimiento.md).
- [Diseña la revisión humana de decisiones y acciones](../bago5-diseno-revision-decisiones/procedimiento.md).
- [Audita y mejora la interfaz React de BAGO](../bago5-interfaz-react/procedimiento.md).
