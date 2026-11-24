---
name: bago5-memoria
description: "Coordina la recuperación y el guardado de memoria del proyecto, respetando el destino y los permisos vigentes."
---

Aplicar una sola vez por misión el ciclo vigente de [bago5-ganchos-sesion](../bago5-ganchos-sesion/SKILL.md) y su [contrato de continuidad](../bago5-ganchos-sesion/references/lifecycle.md); en las derivaciones, reutilizar el binding y estado actuales de proyecto, sesión y memoria. Revisar después únicamente los controles pertinentes al evento y a la tarea, sin reinicializar el ciclo ni recorrer dependencias recursivas. Este enlace no activa todos los especialistas ni autoriza efectos, archivos, persistencia o instalación de hooks; cada operación conserva sus requisitos de alcance, herramientas y autorización vigentes.

Antes de fijar o preparar una versión, runtime o configuración para un destino, o ejecutar una acción que dependa de ellos, aplicar la [comprobación previa del destino](../bago5/references/target-preflight.md); si falta evidencia actual, bloquear solo el trabajo dependiente y continuar lo independiente.

Antes de cualquier operación aplicar [contexto seleccionado](../bago5/references/memory-scope.md). Conservar el proyecto y almacen seleccionados; la derivacion no inicia otro ciclo ni habilita operaciones en otro destino.

# BAGO5 · Memoria persistente y continuidad

La gobernanza BAGO5 identifica objetivo, proyecto, permisos, fuentes, STOP y aceptación; la skill bago5-memoria-viva opera el almacén GENERAL a través del conector de la persona actual. El ciclo general está en [memory-cycle.md](../bago5/references/memory-cycle.md) y se ejecuta una vez por misión, no una vez por cada llamada. No introducir otro orquestador.

Acepta por misión MODO_MEMORIA=LECTURA o MODO_MEMORIA=LECTURA_ESCRITURA; puede haber modo distinto por origen/destino simultáneamente. LECTURA_ESCRITURA solo habilita intentos solicitados por el usuario y autorizados en ese destino; no altera permisos MCP. Sigue el contrato completo en el ciclo general.

## Intención expresa de guardar — prioridad operativa

Aplicar el [contrato de intención y guardado](references/memory-intent.md) ante cualquier formulación semánticamente equivalente a «recuerda», «memoriza», «guarda esto», «consérvalo», «regístralo en memoria», «apúntalo para después», «tenlo presente en el futuro», «no olvides», «actualiza lo que sabes de esto», en el idioma de la conversación, con o sin invocación literal de `$bago5-memoria-viva`. Si es inequívoco que la petición es persistir información, no responder solo «lo recordaré» ni concluir tras guardar en memoria de ChatGPT: intentar escritura real en la Memoria Viva GENERAL seleccionada, en esta misma intervención, si la autenticación, identidad, vinculación, permisos y destino están verificados. Peticiones como «¿recuerdas...?», «¿qué significa memorizar?» o la cita de una frase no autorizan escrituras.

Una solicitud expresa de guardar autoriza la escritura del contenido pedido únicamente en el destino que el usuario haya identificado o autorizado y que pueda verificarse. No autoriza instalar/conectar servicios, usar memoria ajena, alterar otro almacen ni elegir entre destinos ambiguos. Si el destino no está verificado, distinguir BLOQUEADO de guardado efectuado; no afirmar éxito. La autorización de almacenamiento en ChatGPT no constituye autorización para un almacén externo diferente cuando no ha sido seleccionado.

## Federación y selección de destino

Para múltiples memorias, compartir, invitaciones, exportar/importar o `$memoria-codex`, consultar [bago5-memorias-conectadas](../bago5-memorias-conectadas/SKILL.md). No equiparar conectores del host con alias SQLite ni inferir privilegios de URLs. Ante varios almacenes, exigir selección de destino antes de operaciones externas; la mera coincidencia temática no decide. El gestor Python opcional no se instala automáticamente. Las operaciones remotas sin endpoints reales de invitación o exportación completa quedan BLOQUEADO/NOT_RUN para ese servicio. ALIFE PHP es el destino principal opcional; Sites no es una dependencia ni una alternativa automática.

## Identidad y lectura inicial

Usar exclusivamente la Memoria Viva seleccionada, autenticada y vinculada a la persona actual o compartida con autorizacion verificada; nunca otro almacen ni el Site del creador como fallback. Aplicar [onboarding](../bago5/references/onboarding.md). Descubrir `list_projects`, `search_memories`, `get_memory` del conector seleccionado y resolver proyecto por ID. La lista de proyectos prueba acceso a registros, no necesariamente propiedad ni permiso de escritura; requerir evidencia suficiente de identidad/vinculación del host. Si no se puede verificar, declarar BLOCKED/NOT_RUN y no escribir. No asignar `General` ante ambigüedad de proyecto. Contrastar recuerdos con fuentes actuales; no elevar la memoria a canon.

## Guardado y comprobación

Los permisos son por tarea y operación; no existe una autorización permanente codificada para Marc ni para otros usuarios. Si la petición actual autoriza guardar avances materiales en un destino identificado y verificado, registrar cada hito pertinente y releerlo. En otro caso, escribir únicamente ante una intención expresa de persistencia dentro de su alcance. No heredar permisos entre conversaciones, reintentos, usuarios o almacenes. La instalación o conexión no autoriza escritura. Respetar «no guardes», «no uses memoria», STOP, solo lectura y revocaciones. Atender las solicitudes expresas de recordar, memorizar, conservar, actualizar, cerrar, reabrir o archivar dentro de su alcance. No guardar conversaciones completas salvo solicitud inequívoca de archivo literal y capacidad real de recuperarlas fielmente. Distinguir contenido literal, observaciones e hipótesis; no presentar una hipótesis como verificada.

Antes de crear, buscar duplicados; antes de editar, obtener la última versión con `get_memory`. Enviar campos íntegros a `save_memory` y `expected_version` para edición; preservar identidad, tipo, fuente, etiquetas, proyecto, fijado, archivo, estado y cierre no afectados. Revisar errores y conflictos; no sobrescribir a ciegas. Releer el ID con `get_memory` tras guardar y comprobar ID, proyecto, contenido y versión. Sin relectura: NO COMPROBADO, no VERIFICADO. Una petición sin datos suficientes no se convierte silenciosamente en otra memoria.

## Estados, aislamiento y continuidad

`status=pending|active|superseded` indica resolución; `decision_closed` indica cierre, `archived` archivado por separado. STOP detiene nuevas acciones. Respetar «no guardes», «no uses memoria», «solo lectura» y revocaciones. Identidad, autorización y selección deben comprobarse por usuario y misión: no heredar permisos entre chats, personas ni memorias. No convertir decisiones en objetivos automáticamente. Un handoff nunca transfiere permisos. Al cierre informar por separado: memoria ChatGPT, Memoria Viva (ID/proyecto/versión/comprobación) y destinos BLOQUEADOS/NOT_RUN.
