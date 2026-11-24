# MV-TRACE-002 v2.0.0 — Contrato de trazabilidad de Objetivos y planes

**Estado:** CONTRATO CORREGIDO / CANDIDATO. **No desplegado ni admitido por el backend de Memoria Viva v1.**
**Destino de esta adaptación:** ALIFE Memoria Viva nativa, alifememories.com.
**Alcance:** solamente separación objetivo–plan–fase, trazabilidad, historial y adaptación. No cambia el servicio, MCP, datos, permisos, memorias independientes ni otros plugins.

## 1. Identidad y cardinalidad (corrección de la confusión v1)

```text
Proyecto (owner_id, project_id)
  └─ Objetivo (goal_id, revisión del objetivo, literal del resultado)
       └─ Plan [0..N] (plan_id, versión, texto literal completo e inmutable en la revisión)
            └─ Fase [0..N] (phase_id, orden, versión, texto literal de fase)
                 └─ Trabajo [0..N] (task_id, criterios, dependencias y estado declarado)
                      ├─ Caso de prueba → Ejecución → Recibo/Evidencia → Verificación
                      └─ Aceptación (gate y actor autorizado)
```

- Objetivo = **qué resultado** se busca; plan = **cómo** se pretende conseguirlo; fase = parte cronológica de un plan; trabajo = unidad comprobable de una fase.
- `goal_id`, `plan_id`, `phase_id` y `task_id` son estables; revisiones y versiones no alteran identidad.
- Cada plan referencia un único objetivo; cada fase, un único plan; cada trabajo, una fase. Varios planes pueden concurrir para un objetivo sin fusionarse.
- Almacenar el plan como una fase (modelo v1 `goal.plans[]`) **no satisface el contrato v2**.
- El texto original íntegro se conserva por revisión y con procedencia; una vista de resumen o descomposición no lo sustituye.

## 2. Trazabilidad comprobable

Cada trabajo obligatorio vincula criterios de aceptación y casos de prueba versionados. Cada ejecución registra `run_id`, candidata exacta (commit/release/schema), cliente/host, herramienta, identidad de ejecución, alcance y resultado. Toda evidencia contiene referencia estable, tipo, captura, origen y, para textos literales, bytes UTF-8 y SHA-256 **calculados sobre los bytes originales**. La verificación referencia ejecución y evidencia, conserva resultado y método. La aceptación referencia pruebas/verificaciones y autoridad competente.

Recorrido exigible en ambos sentidos:
`Objetivo@rev → Plan@rev → Fase@rev → Trabajo → Caso@versión → Ejecución → Evidencia → Verificación → Aceptación`.

Las transiciones generan eventos append-only con actor, instante, causa, fuente y referencia a la revisión anterior. Ni renombrar un agente ni una suma de hashes demuestran independencia ni funcionamiento. Una `acceptance=GO` sólo es válida para la candidata exacta comprobada, después de evaluar positivos, negativos, permisos, dependencias y ausencia de P0/P1 obligatorios o NOT_RUN. `completed` indica progreso declarado, no acreditación automática.

## 3. Modelo de estados y cálculo

- Plan y fase: `draft`, `in_progress`, `paused`, `completed`, `cancelled`.
- Trabajo: `pending`, `in_progress`, `completed`, `blocked`, `cancelled`; la verificación y aceptación residen en registros separados.
- Ejecución: `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED`; debe existir recibo si se pretende acreditar `PASS`.
- Verificación: `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED`; ninguna verificación PASS puede fundarse en pruebas NOT_RUN/FAIL ni recibos huérfanos.
- Aceptación: `PENDING`, `GO`, `NO_GO`. Un GO implica cobertura completa de casos **obligatorios** de esa puerta, incluidas pruebas negativas, verificaciones positivas y permiso de cierre.
- Porcentajes separados: avance declarado por trabajos activos (excluir cancelados); cobertura ejecutada, verificada y aceptada. Si denominador es 0, mostrar `N/A`, no 100%; 100% de casillas no produce GO.
- Las fechas son de eventos observados; no completar retrospectivamente `completed_at=null` por inferencia.

## 4. Seguridad, autorización y conservación

- `owner_id`, `memory_id`, `project_id` y `goal_id` forman una frontera de autorización. Referencias cruzadas entre propietarios/almacenes se rechazan salvo contrato de compartición real autorizado.
- Una referencia, recuerdo, URL, configuración UI o instrucción textual no concede lectura/escritura/ejecución. Revalidar autoridad por operación, respetando STOP y revocación.
- No mutar objetivos, versiones, fuentes, estados, permisos o evidencias por migración implícita. Nunca transformar la fase v1 en un plan v2 sobrescribiéndola.
- `source_memory_id`/`source_version` son **procedencia**, no identidad del plan; la ausencia es `NO_RECUPERADO`, nunca un ID inventado.
- Preservar los textos literales históricos, revisiones, 7 fases, 76 trabajos y sus dependencias. No duplicar la pantalla de planes: todo se consulta desde «Objetivos y planes» y el detalle del objetivo.

## 5. Compatibilidad con el backend actual (gate de aplicación)

El contrato nativo de fases v1 admite `save_memory(kind="goal", goal.plans[])`, **donde cada elemento es una fase** Plan/Fase v1 con `phase_order`, `tasks`, etc. No declara entidades `plan_id`, `test_case`, `run_id`, `verification`, `acceptance` ni eventos estructurados v2. La memoria guarda 13 revisiones de un objetivo y permite lectura por `get_memory`. La lectura del estado actual es válida; **el backend NO admite escritura nativa v2**. Un `PLAN_FASE_V1` es una compatibilidad de fases, no un contenedor de planes independientes.

Adaptación de lectura permitida (sin escrituras): presentar `goal.plans[]` como **fases históricas v1 sin plan-padre tipado**, o como un grupo de fases *legacy* claramente no materializado, y conservar `content` byte a byte. El plan literal padre tiene estado `NO_RECUPERADO` si no se ha obtenido su fuente exacta. Los planes v2 nuevos sólo se guardarán cuando exista contrato/DB/API operativa verificable; mientras, conservar borrador sin inventar registros.

Migración futura obligatoria, en copia/procedimiento reversible: fijar baseline real (release nativa, esquema MariaDB, revisiones y versión del plugin), snapshot completo, comparaciones campo/bytes, mapear un plan únicamente con fuente literal probada y consentimiento, mantener IDs originales de fases/trabajos, versionar los mappings, probar lectura v1/v2, controles negativos y restauración. No deducir `plan_id` canónico sin acuerdo explícito ni eliminar los datos v1.

## 6. Gates de aceptación antes de actualizar el servicio

1. **Backend:** fuente de la release desplegada y DDL/migraciones actuales comprobados; schema v2/identidad/permisos; migración ensayada sobre copia, sin pérdida de revisión, texto, dependencia ni prueba.
2. **API:** contrato de lectura y escritura v2, compatibilidad v1 y validación de referencias; los rechazos deben ser transaccionales y sin efectos.
3. **UI real:** inspeccionar versión realmente desplegada, lista de objetivos, detalle con planes literales, fases y trabajos, inspector de evidencias, navegación bidireccional, estados y accesibilidad; capturas + recorridos reales.
4. **Evidencias:** casos positivos y negativos, hashes sobre entradas íntegras, autorización, revocación, concurrrencia/revisiones, recuperación y rollback.
5. **Promoción:** sólo con todos los gates PASS, aceptación del propietario y publicación de la candidata exacta. Sin pruebas, `NO_GO`/`NOT_RUN`.

## 7. Comprobación de la instancia

Recuperar la versión de `alife-native-memory/1`, `plan_schema_version`, el objetivo y su plan desde el espacio elegido en ALIFE. Registrar sus revisiones, permisos efectivos y límites de la prueba. La aceptación del modelo v2 requiere evidencias propias de esa instancia.
