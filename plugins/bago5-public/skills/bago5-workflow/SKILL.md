---
name: bago5-workflow
description: "Seleccionar las habilidades necesarias para una consulta o tarea con una política verificable."
---

# Seleccionar las habilidades necesarias para una consulta o tarea con una política verificable

El [selector](scripts/route_suite.py) interpreta la [política de rutas](references/route-policy.json). Una consulta simple usa `question`. Para una tarea selecciona `repository`, `goal`, `phased`, `app_game`, `repair` o `ui`. Los módulos adicionales de `--include` deben estar permitidos por la política y justificados por el encargo.

Desde esta habilidad usa `python scripts/route_suite.py --intent repository --reason "revisar la candidata" --request-id revision`. El recibo muestra los archivos seleccionados y el hash de la política. Añade `--receipt` con una ruta nueva solo si se requiere conservarlo. El [perfil CLI opcional](references/codex-profile.md) prepara un perfil aislado después de comprobar el catálogo de habilidades.
