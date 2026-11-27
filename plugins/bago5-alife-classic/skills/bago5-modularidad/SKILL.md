---
name: bago5-modularidad
description: "Revisa responsabilidades, duplicaciones y dependencias entre módulos; propone o aplica cambios autorizados."
---

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# BAGO5-MODULARITY

Aplicar bago5 y el contrato GPT Classic.

Inventariar modulos y consumidores del proyecto accesible. Longitud de archivo es solo indicio: demostrar responsabilidades mezcladas, limites inestables, duplicacion semantica o dificultad de prueba antes de proponer extraccion. Comparar comportamiento y contratos; no centralizar variaciones de dominio intencionales.

Definir propietario, contrato publico, direccion de dependencias, consumidores, migracion incremental y regresiones. Mantener autoridad de backend, navegacion, transporte y estado persistente salvo cambio autorizado. Clasificar PROCEED, ARCHITECTURE_GUIDED o HANDOFF_REQUIRED con motivo concreto. ARCHITECTURE_GUIDED permite continuar dentro del limite acordado.

No suponer agentes o scan_monolith_candidates.py instalados. Usar lectura y herramientas disponibles; un escaner solo se ejecuta tras localizarlo y revisar su alcance. Para refactor autorizado comparar imports y contratos antes/despues y probar los consumidores afectados. Verificacion independiente requiere revisor distinto real. Referir desarrollo a bago5-desarrollo y cierre a bago5-verificacion.

En Codex, aplica el [formato de respuesta de BAGO](../bago5/SKILL.md#respuestas-en-codex) al comunicar el resultado.
