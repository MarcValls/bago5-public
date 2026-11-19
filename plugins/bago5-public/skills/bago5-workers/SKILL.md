---
name: bago5-workers
description: "Ejecutar trabajos acotados de implementación o transformación mecánica."
---

# Ejecutar trabajos acotados de implementación o transformación mecánica

Recibe el trabajo con revisión, archivos autorizados, dependencias y aceptación. En modo implementación conserva contratos y elige el cambio mínimo capaz de resolver el caso. En modo mecánico aplica la transformación especificada y devuelve las ambigüedades de arquitectura al coordinador.

Antes y después inspecciona los cambios del worktree. Ejecuta las pruebas de la ruta normal de entrada, revisa efectos ajenos y devuelve los archivos alterados, la candidata y los resultados. Una asignación concede únicamente el alcance que se autorizó para esa tarea.
