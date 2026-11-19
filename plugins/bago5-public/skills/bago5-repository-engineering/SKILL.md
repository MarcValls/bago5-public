---
name: bago5-repository-engineering
description: "Gestionar cambios de repositorio con base, alcance, verificación y recuperación."
---

# Gestionar cambios de repositorio con base, alcance, verificación y recuperación

Usa `repo.resolve_baseline` para identificar repositorio, remoto, revisión, rama, worktree y estado modificado. En `repo.audit` contrasta fuentes y requisitos con la implementación. En `repo.plan_change` delimita rutas, contratos y criterios de aceptación antes de `repo.apply_change`. Conserva las ediciones de otros colaboradores.

En `repo.verify_change` prueba la candidata exacta y revisa el diff. En `repo.govern_change` separa decisión, autorización y ejecución. Si un cambio falla, usa `repo.contain_or_rollback` según el procedimiento autorizado. `repo.prepare_handoff` entrega revisión, resultados, riesgos y trabajo abierto. Estos nombres designan procedimientos que se realizan con las herramientas efectivas del host.
