---
name: bago5-agent-relay
description: Reparte trabajo entre agentes y entrega a otra sesión una tarea con alcance y aceptación explícitos.
---

# Coordinar un relevo

1. Identifica la candidata, una unidad de trabajo, la persona o agente responsable y las verificaciones esperadas. Asigna un único responsable de escritura por archivo o componente.

2. Comprueba que el host ofrece delegación y que el encargo la permite. Entrega únicamente las entradas, permisos y límites pertinentes. Si el destino es otra sesión, prepara un mensaje que pueda interpretarse por sí solo y distingue preparación, envío y recepción.

3. El receptor devuelve rutas relativas, acciones ejecutadas, resultados, riesgos y lo pendiente. El [esquema de relevo](references/worker-handoff.schema.json) define los campos para un recibo estructurado.

## Criterio de cierre

Antes de aceptar el relevo comprueba candidata, alcance, cambios y evidencias. Si dos agentes reclaman la misma tarea, suspende esa escritura y reconcilia el propietario con el registro disponible.

