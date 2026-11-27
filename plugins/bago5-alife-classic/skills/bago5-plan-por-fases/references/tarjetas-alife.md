# Plan/Fase v1 — compatibilidad heredada y trazabilidad v2

**Contrato candidato:** [Contrato de trazabilidad v2](contrato-alife-v2.md) (`MV-TRACE-002`, v2.0.0). **NO ACTIVO** en el servidor actual. Consultar el contrato y su [esquema de trazabilidad v2](../schemas/traceability-v2.schema.json) antes de definir un plan independiente.

**Separación obligatoria:** objetivo = resultado; plan = procedimiento textual completo, versionado e independiente; fase = etapa dentro del plan; trabajo = unidad verificable. Un objetivo puede contener varios planes. No crear una pantalla independiente de planes; mostrarlos bajo cada objetivo. **No afirmar que el MCP v1 soporta entidades plan, ejecución, evidencia, verificación o aceptación.**

**Puerta de compatibilidad:** el backend observado admite `goal.plans[]` como **fases v1**, no como planes autónomos. Hasta verificar la existencia de API y persistencia v2 reales, usar el procedimiento v1 exclusivamente para conservar/editar fases existentes con `id` y `expected_version` recuperados, preservando el contenido literal. Los nuevos planes como entidad padre quedan como borrador preparado, NO GUARDADO; no convertirlos en una fase para conseguir una escritura. Si la fuente de un plan literal completo falta, declarar `NO_RECUPERADO` en vez de construirlo concatenando fases. No migrar ni modificar silenciosamente el objetivo.


## Lectura y actualización en alifememories.com

Usar la app ALIFE Memoria Viva nativa, con recurso OAuth `https://alifememories.com/mcp`. Consultar `get_memory_identity` y cotejar `memory_id`, el proyecto y los permisos efectivos. Leer el objetivo y el registro literal por su ID nativo. Cuando el plan figure como contexto, conservar su ID, versión y texto, y vincularlo desde el objetivo con una referencia al registro. Mantener la procedencia histórica en sus propios campos.

## Actualizar las tarjetas de Objetivos y planes

Al pedir «actualiza el progreso», «marca una tarea» o «cierra una fase», el destino es la tarjeta estructurada que muestra la interfaz. Usa su título, `phase_order` e ID recuperados del objetivo. La numeración visible empieza en uno y puede diferir del ID. Una etapa previa descrita solo en el plan literal se informa por separado y no cuenta como cierre de una tarjeta.

1. Relee el objetivo con `get_memory` y confirma espacio, proyecto, versión y permiso de escritura. Localiza la fase en `goal.plans[]` y los trabajos en `tasks[]` por ID estable. Anota estado, dependencias, criterios y contador antes del cambio.
2. Envía un parche mínimo por ID mediante `patch_memory`, con `expected_version` igual a la revisión recién leída. Para un trabajo edita `patch.goal.plans[].tasks[].fields.status` y su `evidence`. Para cerrar la tarjeta edita `patch.goal.plans[].fields.status` a `completed` cuando se cumplan sus criterios, dependencias y trabajos obligatorios. Si corresponde cerrar el último trabajo y la fase, envía ambos en el mismo parche.
3. Conserva los literales del objetivo y del plan. Excluye `patch.content` y el `content` de la fase de las operaciones de progreso. Si solo hay evidencia parcial, adjúntala al trabajo correspondiente, conserva el estado que justifiquen las pruebas e identifica el criterio pendiente. Si el campo está lleno, conserva la evidencia previa por referencia verificable al historial antes de resumirla.
4. Relee la revisión guardada. Verifica los IDs y campos modificados, el estado de la tarjeta y los trabajos completados sobre el total activo. Informa el antes y el después. Si solo cambió evidencia, di expresamente que el contador sigue igual. Una nota en el objetivo o un hito documental por sí solos no completan una fase visible. Ante conflicto de versión, relee y reconcilia. Con permisos de solo lectura, informa el bloqueo y el parche pendiente.

Forma del parche para una tarea completada (sustituir los marcadores por valores leídos y evidencia comprobada):

```json
{"id":"<objetivo>","expected_version":1,"patch":{"goal":{"plans":[{"id":"<fase>","tasks":[{"id":"<trabajo>","fields":{"status":"completed","evidence":"<prueba y recibo de esta tarea>"}}]}]}}}
```

## Estructura que deben compartir los agentes

- El **objetivo** es un único registro `kind: goal`. `title` y `content` describen el resultado buscado y conservan su formulación literal. `goal` contiene `origin`, `state`, `domain`, `criteria`, `evidence`, `occurred_at` y `plans`.
- En el backend **legado v1**, cada entrada de `goal.plans` es una **fase histórica**, no un plan independiente. No se crea un registro por fase ni por trabajo. `phase_order` sólo ordena las fases del legado. En el contrato **v2** cada plan es una entidad padre propia y contiene fases.
- Cada fase v1 incluye `schema_version: 1`, `phase_order`, `id`, `title`, `phase_goal`, `deliverable`, `acceptance_criteria`, `depends_on_phases`, `content`, `status`, `version` y `tasks`.
- Cada trabajo está dentro de `tasks` e incluye `id`, `title`, `description`, `status`, `acceptance_criteria`, `evidence` y `depends_on`.
- Fases: `draft`, `in_progress`, `paused`, `completed`, `cancelled`. Trabajos: `pending`, `in_progress`, `completed`, `blocked`, `cancelled`. `completed` es un estado declarado; no equivale a verificación.

## Cuándo llega antes el plan que el objetivo

Si todavía no se ha descrito el objetivo, conserva el plan como borrador en el contexto de trabajo. No inventes el objetivo ni lo guardes como fase suelta. Cuando el usuario describa el objetivo, vincula las fases explícitas a ese resultado y guarda el objetivo con sus fases en una sola operación. Mantén la distinción entre lo que pidió el usuario y los campos estructurados: no inventes entregables, criterios, tareas, dependencias ni evidencias. Si un dato obligatorio no está disponible, pregunta o deja el borrador sin guardar.

## Envío a Memoria Viva

1. Inspecciona el esquema de `save_memory` disponible en la sesión. Si acepta directamente los campos v1 anteriores, envíalos así.
2. Si el conector expone el esquema anterior de `goal.plans` y solo admite `id`, `title`, `status`, `version` y `content`, usa su sobre de compatibilidad. Conserva esos cinco campos en el nivel exterior. En `content` coloca exactamente `PLAN_FASE_V1`, seguido por un salto de línea y un objeto JSON completo de fase v1. El `content` interior del objeto JSON contiene el texto literal íntegro del plan.
3. Los valores exteriores de `id`, `title`, `status` y `version` deben coincidir exactamente con los mismos campos del JSON interior. El servidor comprueba esa coincidencia, valida el objeto v1 y almacena la fase normalizada; nunca almacenes el sobre como texto del plan.
4. No envíes prosa libre como `content` exterior ni uses otro envoltorio, nombres de campos o estados. Si la herramienta rechaza el sobre o no permite conservar todos los campos, detente y deja el plan como borrador; no lo reduzcas silenciosamente al formato antiguo.

Ejemplo de sobre (el bloque `<FASE_V1_JSON>` debe sustituirse por JSON real, no conservarse como marcador):

```json
{
  "id": "fase-1",
  "title": "Preparación",
  "status": "draft",
  "version": 1,
  "content": "PLAN_FASE_V1\n<FASE_V1_JSON>"
}
```

## Reglas de consistencia

- IDs de fase únicos y estables; `phase_order` único y ordenado. Una fase solo puede depender de fases anteriores.
- IDs de trabajo únicos dentro de su fase; dependencias solo a trabajos de esa misma fase y sin ciclos.
- Conserva íntegro el plan literal en cada `content` interior. Los campos estructurados lo describen, no lo sustituyen.
- No deduzcas trabajos desde prosa general. Registra solo trabajos expresamente definidos o aceptados por el usuario.
- Los porcentajes se calculan a partir de trabajos activos registrados. Los estados `cancelled` quedan fuera del denominador; sin trabajos activos, no afirmes porcentaje.
- No presentes un porcentaje, un estado `completed` o una evidencia aportada como prueba de verificación. Usa solo el estado que la evidencia permita sostener.

## Trazabilidad y aceptación por alcance

No dar `PASS/VERIFIED/GO` por una casilla `completed`: obtener casos versionados, ejecución real, recibos completos, verificador y aceptación autorizada. Exigir IDs reversibles y procedencia `objetivo@revisión → plan@versión → fase → trabajo → caso → ejecución → evidencia → verificación → aceptación`. Conservar las revisiones recuperadas, los IDs de fase y trabajo y el alcance documental de los cierres históricos. Sin API v2, los identificadores de prueba/recibo no se inventan ni se escriben en campos incompatibles.

Antes de actualizar el servicio nativo, contrastar **fuente de la interfaz realmente desplegada**, **DDL y migraciones aplicadas**, firma MCP real, ACL, semántica de estados y recorrido UI real. Un prototipo y una skill no acreditan esa funcionalidad. Si falla acceso, fuente o prueba, `NO_RECUPERADO/NOT_RUN/NO_GO`; conservar la aplicación vigente.
