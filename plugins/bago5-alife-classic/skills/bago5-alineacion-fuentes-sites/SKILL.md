---
name: bago5-alineacion-fuentes-sites
description: "Contrasta las fuentes de ChatGPT Sites con repositorio, plantillas, plugin y memoria antes de afirmar su alineación."
---

Especialidad opcional solo para una solicitud explícita sobre un proyecto Sites. El alta, la memoria personal, Vault y los ensayos de ALIFEMEMORIES usan el servicio nativo.

Aplicar una sola vez por misión el ciclo vigente de [bago5-ganchos-sesion](../bago5-ganchos-sesion/SKILL.md) y su [contrato de continuidad](../bago5-ganchos-sesion/references/lifecycle.md); en las derivaciones, reutilizar el binding y estado actuales de proyecto, sesión y memoria. Revisar después únicamente los controles pertinentes al evento y a la tarea, sin reinicializar el ciclo ni recorrer dependencias recursivas. Este enlace no activa todos los especialistas ni autoriza efectos, archivos, persistencia o instalación de hooks; cada operación conserva sus requisitos de alcance, herramientas y autorización vigentes.

Antes de fijar o preparar una versión, runtime o configuración para un destino, o ejecutar una acción que dependa de ellos, aplicar la [comprobación previa del destino](../bago5/references/target-preflight.md); si falta evidencia actual, bloquear solo el trabajo dependiente y continuar lo independiente.

# BAGO5 · Alineación de fuente para proyectos Sites

## Alcance

Aplicar esta skill al iniciar y cerrar cualquier trabajo de desarrollo, revisión, reparación o evolución de un proyecto existente en ChatGPT Sites, y a proyectos nuevos cuando ya exista una fuente externa. No modifica contratos ni fuerza una estructura común entre proyectos. Respeta AGENTS.md, la autoridad del proyecto, la jerarquía de fuentes, STOP y permisos.

## Revisión al iniciar cada trabajo

1. Identifica el Site exacto con su `project_id`, título, URL viva/preview y rol de la persona. No derives IDs desde el título o el dominio.
2. Recupera la última versión guardada del Site y registra número, `source.commit_sha`, despliegue cuando esté disponible y fecha de consulta.
3. Resuelve la fuente canónica del proyecto desde las instrucciones del proyecto, `.openai/hosting.json`, la vinculación real del Site o una decisión explícita del usuario. Comprueba repositorio, proveedor, rama y HEAD actual en la fuente autorizada. Un repo temáticamente parecido o la URL pública del Site no demuestra vinculación.
4. Localiza las plantillas, plugins, contratos y recuerdos de proyecto que la solicitud relacione. Registra sus versiones/rutas y respeta sus propias fuentes de verdad.
5. Coteja cada par solo cuando hay evidencia de que comparte origen. Compara commits, archivos/manifiestos o hashes reproducibles y usa estados `COINCIDE`, `DIFIERE`, `NO_COMPROBADO` o `NO_RECUPERADO`. Un commit de Appgen no tiene que ser el mismo que un repo independiente. No declares sincronización a partir de nombres, fechas, resumen, hash sin contenido asociado, captura o despliegue.
6. Si un conector solo expone versión y commit pero no los archivos fuente, registra `NO_RECUPERADO`; no reconstruyas la fuente a partir del HTML público, capturas ni artefactos de build como si fueran los fuentes originales. Continúa el trabajo independiente y acota el bloqueo.

Mantén el registro compacto y trazable: proyecto/Site ID, repositorio y rama, HEAD, Site version y commit, rutas/versions de plantilla y plugin, referencia de Memoria Viva seleccionada, fecha, resultado de cada comparación y fuentes leídas. No guardes tokens, credenciales, datos personales innecesarios ni código completo duplicado en Memoria Viva.

## Repositorio integrado y organización del proyecto

Cuando se solicite reunir varios componentes de un producto en GitHub —por ejemplo, Site, plantilla, plugin y documentación/recuerdos— trata el repositorio como una posible fuente integrada solo después de verificar el alcance, permisos, licencias, relaciones y fuentes originales de cada componente. Recupera y aplica primero las instrucciones del workspace (por ejemplo, `M:\\AGENTS.md` y `M:\\ARBOL_Y_RESPONSABILIDADES.md` si pertenecen al proyecto). No inventes carpetas, no muevas componentes por semejanza de nombres y no copies secretos ni recuerdos personales completos al repo. Usa referencias/versiones de Memoria Viva que apunten a revisión y ruta cuando sea suficiente. Si faltan las instrucciones o fuentes originales, registra `PENDIENTE/NO_RECUPERADO` y prepara una propuesta de árbol con ubicaciones aún por confirmar; no declares el monorepo materializado.

## Catálogo canónico de plantillas en Alife

Cuando el proyecto utilice plantillas del ecosistema Alife/Memoria Viva, Alife Memories es el origen canónico obligatorio: todos los consumidores deben resolver allí el ID y la versión registrada antes de usar una plantilla. El catálogo debe vincular versión semántica, paquete/fuente, commit o revisión, SHA-256 reproducible, versiones de Memoria Viva compatibles, estado y evidencia de verificación. Sin registro consultable en Alife, la plantilla queda `NO_REGISTRADA/BLOQUEADA` para adopción; no la declares compatible ni uses un duplicado de GitHub o de un plugin como autoridad. GitHub puede conservar una copia de trabajo/mirror, siempre vinculada al registro de Alife y cotejada por versión/hash; Alife conserva la autoridad sobre qué versión se distribuye.

El Site Alife v26 ya publica un catálogo de releases y rutas de migración: `GET /api/templates`, `GET /api/templates/{template_id}/{version}`, `GET /api/templates/compatibility` y `GET /api/schema-migrations`; el MCP del Site declara `alife_list_templates`, `alife_get_template`, `alife_check_template_compatibility` y `alife_list_schema_migrations`. Las operaciones de escritura requieren el rol de catálogo y validan manifiesto, URL canónica y hashes. Comprueba qué herramientas expone realmente el host en esta sesión: si aún solo aparecen conexiones, clasifica `API_DEPLOYED_BUT_TOOL_NOT_EXPOSED`, usa una lectura pública de la API si está permitida y no simules escrituras MCP. No registres una URL como si fuera release ni afirmes que el plugin la consulta automáticamente.

## Control de divergencia y migraciones

Para Sites integrados con Memoria Viva o plantillas Alife, registra compatibilidad por la tupla exacta `template_id/version + component_id/component_version + contract_id/contract_version + schema_version`. Los cambios de Site, API, plugin, plantilla o esquema requieren una nueva comprobación; nunca heredan un PASS ni se resuelven con `latest`. El manifiesto de release debe declarar cada objetivo que debe cubrir antes de publicar. Alife conserva el registro y los artefactos; Memoria Viva conserva los datos del usuario.

Las migraciones deben ser explícitas, aditivas siempre que sea posible, idempotentes y auditables. La ruta debe tener versión de origen y destino, artefacto con SHA-256, evidencia de pruebas, requisito de copia de seguridad y estrategia de recuperación. No se ejecutan desde el catálogo central sobre memorias externas. El servicio propietario aplica la migración después de verificar identidad, backup y consentimiento; después comprueba IDs, contenido literal, historial, relaciones y permisos. Si no hay ruta probada, bloquea la actualización y conserva el estado de origen.

## Cambios y actualización

Cuando la tarea incluya editar código y las herramientas den acceso real a la fuente canónica, cambia esa fuente, conserva capacidades e invariantes, compara el diff con el baseline, ejecuta las comprobaciones solicitadas/autorizadas y registra los commits exactos. Después actualiza la vinculación de Site/plantilla/plugin/memoria que el proyecto requiera. Un cambio de código local, un commit, una versión guardada y un despliegue son hechos distintos; informa cada estado por separado. No despliegues ni cambies audiencia como efecto implícito de cotejar versiones.

## Modo chat sin escritura

Si el chat no puede modificar los fuentes, incluye en la respuesta una sección titulada exactamente **Sugerencias de cambios**. Para cada sugerencia indica:

- archivo/ruta o componente afectado; si falta, `NO_RECUPERADO`;
- cambio propuesto o diff legible, evitando inventar código contextual que no se haya recuperado;
- motivo y relación con el objetivo;
- dependencias, invariantes o comportamiento que debe preservarse;
- criterios de aceptación y pruebas/checks que siguen `NOT_RUN`;
- estado `PROPOSED` o `PREPARED`, sin decir aplicado/actualizado.

## Cierre

Antes de cerrar vuelve a comprobar HEAD/Site version y registra si la tarea cambió la relación. Si no hubo cambio de fuente, informa que el cotejo fue solo una lectura. Conserva conflictos como tales. Cada afirmación de coincidencia debe enlazar fuente, revisión/archivo, evidencia de comparación y alcance. Usa la skill de desarrollo/verificación adecuada para cambios materiales; esta skill no convierte una propuesta en código ni en despliegue.

Las consultas al catálogo o a las conexiones de cuenta requieren el complemento BAGO5 ALIFE Gestor y su consentimiento propio.

En Codex, aplica el [formato de respuesta de BAGO](../bago5/SKILL.md#respuestas-en-codex) al comunicar el resultado.
