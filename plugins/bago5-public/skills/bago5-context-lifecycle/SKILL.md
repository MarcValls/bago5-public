---
name: bago5-context-lifecycle
description: Recupera, actualiza y transfiere el contexto verificable de un proyecto durante una tarea.
---

# Mantener el contexto del proyecto

1. Al entrar identifica la petición, el proyecto dueño, su fuente autorizada y el estado observable actual. Lee el último relevo solo si corresponde a esa identidad.

2. Reconcilia decisiones, revisiones y cambios locales con la candidata. Conserva referencias al estado anterior cuando una decisión quede sustituida. Mantén inferencias y hechos identificables.

3. Durante la tarea registra solo los cambios de contexto necesarios para continuar. Antes de reanudar comprueba revocaciones, bloqueo, dependencias y condiciones de aceptación.

## Criterio de cierre

Entrega una síntesis con candidata, decisión vigente, comprobaciones y trabajo pendiente. Si se autorizó guardar continuidad, relee el registro de destino y confirma que corresponde al mismo proyecto.

