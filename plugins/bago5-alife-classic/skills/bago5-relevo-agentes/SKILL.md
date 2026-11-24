---
name: bago5-relevo-agentes
description: "Coordina delegaciones y relevos entre agentes o sesiones, conservando alcance, permisos y evidencias."
---

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# Colaboración y handoff

El agente principal conserva la misión y la autoridad. Antes de delegar fija candidata, objetivo, criterios, permisos ya concedidos, archivos o preguntas acotados, exclusiones y evidencias esperadas. Workers lógicos no reciben permiso para efectos externos por su rol.

Usa herramientas nativas de colaboración solo si el host las expone y la petición autoriza su uso. Mantén cada work item con ID, candidato, alcance y dueño; evita escrituras concurrentes sobre los mismos archivos. Exige un handoff con cambios, comandos realmente ejecutados, recibos, fallos y riesgos; valida ese handoff antes de usarlo. Un resumen no es verificación independiente.

## Dos mecanismos distintos de continuidad

No mezclar el relevo entre hosts con la colaboración local entre workers:

- **GPT/ChatGPT ↔ Codex/Work:** es un relevo entre superficies. Si el otro host debe continuar, preparar un paquete/prompt literal con misión, proyecto, candidata, estado, decisiones, fuentes, restricciones, STOP, permisos no transferibles, aceptación, evidencias y pendientes. El envío es manual salvo herramienta real de mensajería autorizada. Hasta recibir y validar la respuesta: `HANDOFF=PREPARED`, ejecución del receptor `NOT_RUN`.
- **Workers dentro de Codex mediante BAGO5os:** cuando el trabajo requiera colaboración local y la Suite esté realmente instalada, leer y aplicar `optional-runtime/bago-operating-suite/modules/agent-relay/SKILL.md`, su `README.md` y `HOST_ADAPTER_CONTRACT.md`. Usar el controlador `task` y el `TaskStore` existentes; no crear un segundo orquestador, ledger ni almacén de misión.

## Relay local de BAGO5os

La ruta anterior es optativa y está limitada al runtime local. Antes de usarla, comprobar la identidad/versión instalada de BAGO5os, la raíz de proyecto, el estado de la misión, la candidata congelada, el TaskStore, STOP/revocaciones, herramientas reales y permisos del host. La mera presencia del módulo en el plugin no demuestra que la Suite esté instalada o disponible en el equipo.

Cuando la capacidad esté disponible y el alcance lo permita:

1. Leer `modules/agent-relay/SKILL.md`, `README.md` y `HOST_ADAPTER_CONTRACT.md` de la distribución instalada, no de una copia histórica.
2. Reutilizar la misión y el TaskStore existentes. Consultar `task collaborate guide`; tratarlo como guía de admisibilidad, no como autorización ni decisión del agente.
3. Reclamar únicamente el check asignado con el worker real disponible. Mantener `lease_token` privado; nunca incluirlo en prompts, handoffs, logs o evidencias.
4. Recuperar el checkpoint, comprobar el alcance y ejecutar únicamente efectos autorizados mediante el host. Registrar checkpoints y recibos reales.
5. Para relevar, usar `offer`; el sucesor debe aceptar el `handoff_id` y digest exactos mediante `accept`. El handoff no transfiere permisos ni memoria interna del modelo.
6. El ejecutor no se verifica a sí mismo: el check de verificación requiere el rol/verificador separado y evidencia propia. Finalizar checks y cerrar la misión son operaciones distintas.
7. Ante STOP, detener nuevas asignaciones. La revocación de leases no detiene por sí sola procesos externos; el host debe interrumpirlos y reconciliar sus efectos antes de recuperar la misión.

La modalidad implementada por la Suite es cooperativa y serial, no paralela. La demo determinista usa procesos de prueba, no agentes LLM. No están implementados el lanzamiento automático de agentes nativos, la detección automática del límite de contexto ni un daemon autónomo. Si el host no ofrece un worker real, declarar `AWAITING_HOST_WORKER/NOT_RUN` y continuar el trabajo independiente; no fingir que se ha delegado.

## Relevo entre sesiones GPT y Codex

- Si el trabajo corresponde al host actual y sus herramientas bastan, continúa en esa sesión; no mandes al usuario a pegar un prompt en el mismo host, salvo petición expresa.
- Si debe continuar en el otro host, prepara un prompt copiable dirigido a GPT o Codex según corresponda. Antes, termina las comprobaciones y el trabajo independiente que sí puede hacerse aquí.
- El prompt resume misión, proyecto/candidato/versión, alcance, estado, decisiones, fuentes, restricciones, autorización de esta tarea, criterios de aceptación, evidencias y qué debe devolver. Pide al host receptor verificar de nuevo identidad, permisos, STOP, fuentes y capacidades.
- No transfieras credenciales, cookies, tokens, encabezados de identidad ni autorización entre sesiones. No afirmes que el otro host ejecutó el trabajo porque se preparó o pegó un prompt. Hasta recibir y revisar el resultado: handoff PREPARED; ejecución del receptor NOT_RUN.
- El relevo es manual: no envíes mensajes a GPT, Codex ni terceros salvo que exista una herramienta de envío y el usuario lo haya autorizado expresamente.

## Delegación a workers de Codex

Si no hay worker o tool real, prepara el handoff marcado AWAITING_HOST_WORKER/NOT_RUN y sigue el trabajo independiente de la misión principal. No inventes procesos paralelos, daemon, lease o aceptación. STOP revoca nuevas asignaciones; una reanudación requiere petición explícita y conciliación del estado externo. Usa `references/worker-handoff.schema.json` para el artefacto estructurado cuando la sesión autorice escribirlo.
