# Plan agéntico portable

Aplicar al repartir un plan entre responsables en GPT Classic, Codex u otro host comprobado. Reutilizar `bago5-objetivos`, `bago5-plan-por-fases`, los especialistas y el controlador existente compatible. Esta guía no crea procesos residentes, herramientas, permisos ni un nuevo registro de tareas.

Aplicar el [preflight obligatorio de fase](phase-preflight.md) antes de seleccionar el controlador, asignar trabajo, activar agentes o modificar recursos. Comprobar hasta el cierre de la fase, anunciar primero cualquier transición CODEX/WORK/CHAT o intervención humana y distribuir la ejecución completa solo con `GO` vigente. Con `REQUIERE_USUARIO` y `can_prepare`, limitar la asignación a los pasos de preparación ya autorizados y anunciados para producir una candidata revisable; el efecto y la aceptación pendientes siguen bloqueados. Recuperar la base y consultar capacidades en lectura forma parte de esa comprobación; no constituye selección operativa. Cada fase e intento de reanudación requiere su propio dictamen, también cuando se reutilizan responsables del pase anterior.

## 1. Recuperar y fijar la base

- Identificar proyecto, objetivo, plan literal completo, versiones, fase y tareas existentes. Conservar IDs, historial, decisiones e invariantes; no crear un plan paralelo para repartirlo.
- Distinguir petición de planificación, preparación y ejecución. Asignar roles propuestos no ejecuta trabajos ni autoriza despliegues, migraciones o escrituras externas.
- Comprobar las capacidades de fuente y destino: herramientas, identidad, permisos, schema, runtime, entorno y STOP. Usar `NO_RECUPERADO`, `NO_COMPROBADO` y `NOT_RUN` cuando corresponda.
- Si se pide la última versión, cotejar por separado la última versión guardada, el último despliegue `succeeded` y el HEAD de su fuente. Registrar IDs, commits, fecha y fuente de cada dato antes de extraer o integrar y repetir el cotejo antes de publicar. No adoptar una rama sin verificar como versión productiva ni asumir que guardado equivale a desplegado.
- Si aparecen versiones nuevas o diferencias, inspeccionar el delta, conservar cambios de la candidata y actualizar la base de forma explícita. Repetir las comprobaciones afectadas; conservar como históricas las anteriores. Un cierre sobre una candidata ya obsoleta no satisface el requisito de última versión.

## 2. Mantener la semántica del almacenamiento

Objetivo = resultado; plan = procedimiento literal completo y versionado; fase = etapa; trabajo = resultado verificable. Los pases son lotes de ejecución, no una nueva jerarquía de planes o fases.

Comprobar el contrato real del almacén. En Memoria Viva legado `goal.plans[]` contiene fases v1; no admite por ello planes padre v2. Preservar fases existentes mediante IDs y versión esperada. Si falta la fuente literal, no reconstruirla concatenando fases. Un plan nuevo que no pueda guardarse sin pérdida permanece preparado y no guardado; un documento de propuesta no es una entidad v2 implementada. No crear campos, relaciones o recibos que el backend no admite.

Un único registro canónico conserva plan y avance. Si existe un controlador compatible, sus claims y recibos operativos enlazan al mismo trabajo; no se mantienen dos listas independientes de progreso. En ausencia del controlador, no inventar sus eventos ni presentar una conversación como almacenamiento durable.

## 3. Ficha de trabajo y responsabilidad

Preparar cada ficha con datos comprobados o campos explícitamente propuestos. Proyectarla solo a los campos que acepte el schema del destino; no volcar esta tabla como un schema nuevo.

| Campo | Contenido necesario |
|---|---|
| Identidad | Proyecto, objetivo, plan y versión, fase, trabajo; distinguir ID propuesto y persistido. |
| Resultado | Entregable concreto y capacidad que debe quedar disponible. |
| Base | Fuente exacta, candidata/commit, entorno y lectura de vigencia. |
| Responsable ejecutor | Agente real cuando exista; si solo es una asignación propuesta, indicarlo. |
| Coordinador | Un responsable de dependencias, integración y actualización del registro. |
| Verificador | Agente o persona distinta del implementador, alcance y evidencia requerida. |
| Modo preferente y herramientas | CHAT, WORK o CODEX; host real, capacidades expuestas, evidencia, alternativa que conserve el contrato y handoff si hace falta. |
| Dependencias | IDs existentes y gates previos; sin ciclos ni dependencias falsas. |
| Lectura/escritura | Rutas, recursos, entornos y efectos permitidos; excluir solapamientos inseguros. |
| Aceptación | Casos positivos, negativos y de conservación pertinentes, con resultados observables. |
| Evidencia | Candidata, acción real, resultado, referencia y límites; separar inspección de ejecución. |
| Preflight de fase | Dictamen vigente, contexto/intento, evidencia de ejecutar/verificar/entregar, entorno y acción humana pendientes; GO para ejecución completa, o can_prepare exclusivamente para los pasos autorizados de preparación. |
| Riesgos y reversión | Condiciones de bloqueo, qué se puede revertir y prueba necesaria; no prometer rollback. |
| Entrega | Artefactos/diff, comprobaciones ejecutadas, pendientes y siguientes consumidores. |

El coordinador no concede permisos nuevos. Cada ejecutor confirma alcance y herramientas antes de actuar. El verificador no modifica la superficie que verifica; si la repara, debe verificarse esa candidata por otra instancia antes de afirmar independencia. La aceptación del usuario se distingue de la verificación técnica.

### Reparto entre CHAT, WORK y CODEX

Usar estos nombres como perfiles de ejecución solicitados por el usuario, no como garantías de acceso. Identificar la sesión y las herramientas observadas; no deducir el host por el modelo ni asumir que CHAT carece de herramientas o que WORK/CODEX disponen de todas.

| Perfil | Trabajo preferente cuando existan capacidad y autorización | Comprobación previa |
|---|---|---|
| GPT Classic · CHAT | Recuperación por conectores, objetivo/plan/contratos, reparto y seguimiento, revisión, operaciones MCP autorizadas y actualización del plugin si está expuesta. | Identidad de conectores, schemas, lectura/escritura efectivas y operación real; conversación no implica proceso residente. |
| GPT Classic · WORK | Recuperación y edición de fuentes, cambios UI, pruebas con navegador, empaquetado y publicación autorizada cuando sus herramientas lo permitan. | Workspace y candidata, herramientas de edición/ejecución/navegador, fuente y destino de publicación; no confundir preview con producción. |
| CODEX | Repositorio, cambios de backend/port, shell, pruebas, CI, candidata y despliegue mediante SSH u otro canal solo si está realmente expuesto. | Checkout/branch/HEAD/dirty, runtime, permisos, entorno y credenciales del host; disponer de terminal no acredita acceso al hosting. |

Cada trabajo declara su modo preferente, responsable real, herramientas necesarias, evidencia de cierre y alternativa. Si otro perfil puede cumplir el mismo contrato con herramientas comprobadas, puede realizarlo sin cambiar alcance ni aceptación. Si falta una capacidad, preparar handoff con fuentes, candidata, decisiones, STOP, pendientes y evidencias; el receptor repite preflight y comprueba sus propios permisos. La autenticación, los permisos y el estado de una sesión no se transfieren. Un handoff preparado sigue `NOT_RUN` en el receptor hasta observar su ejecución.

## 4. Repartir por dependencias y superficies

1. Reutilizar roles pertinentes, por ejemplo fuente/conservación, contratos/backend, interfaz, conectores/permisos, verificación y promoción. Activar solo los necesarios; un nombre de rol no instala un agente.
2. Resolver primero contratos compartidos y aceptación. Permitir trabajo paralelo solo con dependencias satisfechas, entradas estables, scopes de escritura compatibles y verificación independiente preservada.
3. Si dos trabajos modifican el mismo archivo o contrato, serializarlos o asignar integración a un único responsable. Recalcular el lote después de cada resultado o cambio material.
4. Seleccionar el controlador por su contrato real. El `teamctl` incluido admite `AUDIT`, `REPAIR`, `VERIFICATION`, `PROMOTION`; no introducir `DEVELOPMENT` o `INTEGRATION` ni cambiar la etiqueta del trabajo para hacerlo pasar. No iniciar otro controlador sobre una misión activa.
5. En GPT Classic y Codex aplicar la misma aceptación y trazabilidad, comprobando por separado ejecución, herramientas, permisos y memoria. Con agentes nativos disponibles y autorización aplicable, delegar el lote seguro; sin ellos, trabajar secuencialmente dentro del alcance permitido. Si falta la capacidad material, preparar un handoff y marcar la ejecución afectada `NOT_RUN`.
6. Mantener STOP y revocación entre hosts, agentes y reintentos. La recuperación de contexto, la actualización del plan o un handoff no reanudan un trabajo detenido ni transfieren autenticación.

La equivalencia exigible es de resultado y controles comprobados; no afirmar equivalencia funcional automática entre hosts. Si el controlador requerido no admite la operación, la distribución técnica dependiente queda `NOT_RUN`; los preparativos independientes autorizados pueden continuar con herramientas reales, sin simular claims o recibos.

## 5. Integraciones y conservación

Para trasladar una capacidad entre superficies, comparar capacidad → fuente exacta → ruta de destino → dependencias → contrato/invariante → prueba → evidencia. Mantener separadas integración de interfaz, conexión a un servicio y migración de datos. Integrar una sección no autoriza copiar recuerdos, cambiar propietario, ACL, almacén canónico o endpoints.

En un módulo de memoria, comprobar selección explícita de almacén, identidad, permisos efectivos, lectura/escritura según alcance, errores y revocación. Si una integración carece de transporte autenticado, no sustituirlo por datos de ejemplo, tokens pegados en archivos o una caché local presentada como memoria canónica.

Antes de promoción, exigir la candidata exacta, conservación de capacidades previas, evidencias de los criterios, destino comprobado, reversión revisable y autorización aplicable. Los P0/P1 que afecten al alcance bloquean ese cierre. Un build, un hash o una actualización de plugin no verifican el servicio integrado.

## 6. Entrega y cierre

Antes de preparar la entrega, aplicar la [decisión de turno](../../bago5/references/turn-decision.md). Ejecutar el trabajo local pendiente que siga siendo elegible. Si se pidió únicamente planificar, cerrar al entregar el plan aceptable; si se pidió ejecutar, el reparto o final de un pase no satisface por sí mismo el encargo. Cotejar los criterios de la ficha original con el resultado integrado, manteniendo cada uno como satisfecho, pendiente, bloqueado o dispensado por decisión legítima con motivo.

Entregar plan literal, reparto de responsabilidades, DAG/pases, primeros trabajos listos, bloqueos concretos y criterios de cierre. Mantener la diferencia entre `PROPUESTO`, `PREPARADO`, `IMPLEMENTADO`, `VERIFICADO`, `VALIDADO`, `NOT_RUN` y `BLOQUEADO`.

Presentar cada siguiente acción que realmente deba entregarse con destinatario primero: `CODEX — Siguiente acción: ...`, `WORK — Siguiente acción: ...` o `CHAT — Siguiente acción: ...`. Para el relevo, aplicar [siguiente acción y relevo literal](../../bago5/SKILL.md#siguiente-acción-y-relevo-literal): cuando exista petición de guardado y autorización vigente, guardar el prompt exacto en la memoria del proyecto seleccionado, buscar duplicados, releer y cotejar texto, ID y versión antes de afirmar guardado. El prompt mostrado, el recuperado y el incluido en un paquete deben ser idénticos. Si la operación no está autorizada o falla, mantener explícito el estado del guardado; no elegir otro almacén como fallback.

Cuando haya artefactos que el receptor necesite, entregar un único ZIP suficiente para ese trabajo, con LEEME, prompt literal, inventario, hashes, evidencias y arranque necesarios, sin secretos. Incluir al final el enlace al paquete comprobado siguiendo `bago5-entrega-paquetes`. Si basta el prompt, omitir el ZIP. No duplicar el plan canónico ni fabricar un relevo hacia la sesión actual si puede continuar, salvo petición expresa del usuario.

Al recibir resultados, contrastarlos con la candidata y la ficha original, verificar las evidencias y actualizar solo el registro autorizado. Calcular avance con los trabajos realmente cerrados bajo el contrato canónico; no contar roles asignados, handoffs preparados ni fases redactadas como implementación. El plan termina cuando sus criterios observables se cumplen, no por consumir todos los pases estimados.
