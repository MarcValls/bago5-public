---
name: bago5-plan-por-fases
description: Gestionar objetivos, fases y tareas con su evidencia.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](../bago5/references/controles-especialistas.md#efecto).

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# BAGO5-PHASED

## Preflight obligatorio de cada fase

Antes de seleccionar recursos operativos, asignar agentes/trabajos, activar o modificar nada de una fase, aplicar el [preflight de fase](references/phase-preflight.md). Recuperar e inspeccionar en solo lectura lo necesario para comprobar herramientas, accesos, autorización vigente, dependencias y capacidad real de **ejecutar, verificar y entregar toda esa fase**. Incluir desde el inicio las intervenciones humanas y cambios CODEX/WORK/CHAT que exigiría su cierre. No probar permisos mediante escrituras, instalaciones o publicaciones reales.

Comunicar `GO`, `CAMBIO_ENTORNO`, `REQUIERE_USUARIO`, `BLOQUEADO` o `NO_COMPROBADO` antes de la primera acción operativa. Con `GO`, continuar dentro del alcance autorizado sin otra confirmación. Si faltan entorno, presencia o permiso esenciales, indicar qué, quién, cuándo, por qué y qué comprobación habilitará continuar; la presencia del usuario no satisface una acción pendiente. Repetir al iniciar **cada** fase, reanudarla, recibir un relevo o cambiar condiciones relevantes; un GO de otro host, sesión, intento o fase no se transfiere. Una intervención `BEFORE_START` impide preparar trabajo dependiente. Si solo queda una aceptación `BEFORE_COMPLETION`, anunciarla antes y preparar únicamente el resultado revisable ya autorizado cuando se cumpla la excepción acotada del contrato; conservar `REQUIERE_USUARIO`, la fase abierta y el gate pendiente. No cambiar su aceptación ni solicitar de nuevo el permiso de preparación vigente.

Usar el registro existente o la conversación; no crear archivos ni campos de backend automáticamente. El [comprobador de recibos](scripts/phase_preflight.py) y su [schema local](schemas/phase-preflight.schema.json) verifican coherencia de evidencia declarada cuando puedan ejecutarse; no son un interceptor del host ni prueban acceso por sí mismos. El procedimiento debe comprobar la viabilidad en las fuentes reales; el `GO` del script solo clasifica la coherencia de evidencia declarada. Ninguno acredita éxito futuro ni aceptación; aplicar después las pruebas y gates de resultado.

Aplicar bago5, bago5-objetivos y el contrato GPT Classic. Distinguir objetivo → plan literal versionado → fases → trabajos comprobables. Recuperar los registros existentes y aplicar [Plan/Fase y trazabilidad](references/plan-fase.md) según el esquema comprobado en la memoria seleccionada. La referencia integra la ruta `memoria-viva-plan-fase` para fases históricas v1 y el contrato candidato de intercambio v2.

Para peticiones de plan agéntico, reparto de responsabilidades o ejecución por pases, usar [plan agéntico portable](references/agentic-plan.md). Reutilizar las fases e IDs del plan vigente; los pases son lotes operativos y no crean fases nuevas. Esta referencia prepara asignaciones revisables, no instala agentes, un scheduler ni un controlador.

## Preparar el plan

Antes de ejecutar, recuperar y revisar objetivo, plan literal/version, fases, tareas, orden, dependencias, gates, estados y evidencias. Si la estructura requerida no está persistida, no puede leerse de vuelta o el backend no la admite, la ejecución y asignación dependientes quedan `NOT_RUN`; continuar los preparativos independientes autorizados. Un plan padre nuevo permanece preparado y no guardado cuando solo exista el backend v1.

Cada tarea debe ser una unidad de resultado asignable con ID estable, objetivo/plan/version/fase de origen, descripción, dependencias, responsable/rol propuesto, host y herramienta comprobados, alcance de lectura/escritura, criterio de aceptación, comprobaciones y evidencia requerida. Separar responsable ejecutor, coordinador y verificador realmente independiente. Mantener literalmente los nombres y el orden de fases definidos por el plan. No inventar siete fases ni estados completados por analogía: usar F0–F6 solo cuando esa sea la estructura declarada en la fuente.

Validar el grafo antes de asignar: referencias existentes, ausencia de ciclos, prerequisitos satisfechos, límites de escritura sin solapamiento inseguro y gate de fase explícito. No asignar una tarea bloqueada ni cambiar silenciosamente alcance, orden o contrato. Los criterios ausentes se devuelven como cuestiones concretas o `BLOCKED`, según su impacto.

## Distribuir trabajo

Después de confirmar la estructura admitida y persistida, y con preflight `GO` vigente de su fase o únicamente para los pasos de preparación expresamente permitidos por `can_prepare`, convertir cada tarea del plan (no la fase completa si contiene entregables independientes) en un work item del controlador autorizado y compatible. Incluir objetivo, plan/version cuando exista, fase y tarea origen en la descripción o metadatos admitidos; transportar literalmente criterios, dependencias y evidencias. No añadir campos que el schema del controlador rechace. Mapear funciones a roles existentes y disponibles; nombrarlos no crea agentes, herramientas o permisos.

Comprobar la operación antes de elegir controlador: el teamctl incluido admite `AUDIT`, `REPAIR`, `VERIFICATION` y `PROMOTION`. Un desarrollo o una integración general no se convierte en reparación cambiando su etiqueta. Aplicar [selección del controlador](../bago5/references/controller-selection.md); si no hay adaptación compatible, mantener la distribución técnica `NOT_RUN` y preparar los trabajos mediante las herramientas reales del host sin inventar claims o recibos del runtime.

Calcular lotes con el controlador de equipo existente: solo trabajos READY, dependencias DONE verificadas, scopes de escritura compatibles y verificación independiente preservada. Reutilizar el único controlador elegido para esa misión; no duplicar el estado entre TaskStore, teamctl, conversación y Memoria Viva. Memoria Viva conserva el plan y el avance; el controlador conserva claims, eventos y handoffs operativos. Vincular los dos por IDs de origen y actualizar la ficha canónica después de validar cada resultado.

En Classic, solo lanzar agentes nativos si el host ofrece esa capacidad y existe autorización aplicable. Si no, ejecutar secuencialmente cuando esté permitido; en caso contrario, producir el handoff de asignación y marcar la ejecución como `NOT_RUN`. No describir una propuesta de asignación como trabajo distribuido.

## Objetivos y planes en ALIFE

Para actualizar el progreso de una tarjeta en alifememories.com, aplica el [procedimiento de tarjetas ALIFE](references/tarjetas-alife.md). Resuelve los IDs de fase y tarea con una lectura actual, usa un parche parcial sobre `goal.plans` con la versión esperada y relee el estado y el contador. El literal del objetivo y del plan se conserva durante esta operación.

## Seguimiento y progreso

Aplicar la [decisión de turno](../bago5/references/turn-decision.md) al terminar cada trabajo o pase y antes de redactar el final. Un pase no es por sí solo un límite del encargo. Continuar con el siguiente trabajo local elegible; un bloqueo parcial no detiene trabajos independientes. Cerrar cuando se cumplan los criterios del encargo actual, sin prolongarlo al objetivo mayor. El formato destinatario/siguiente acción solo se usa tras decidir que hace falta relevo o cuando se pide expresamente un prompt.

Para cada tarea pendiente aplicar la [evidencia de cierre y retorno](../bago5/references/turn-decision.md#sustentar-el-cierre-y-retomar-el-encargo): próxima operación y dependencias, o impedimento preciso con fuente actual e intervención mínima. NOT_RUN/NO_COMPROBADO no justifican por sí solos parar el pase. Después de una intervención humana, comprobar su resultado y retomar sin pedir de nuevo permisos vigentes; no dar por cumplida la aceptación por un «hecho», una configuración visible o una memoria histórica. Trabajo independiente solo sin PRIVATE, gate cerrado o STOP y sin exposición de secretos. En Work este control lo aplica el agente; no existe un interceptor del plugin que garantice su ejecución.

Al relevar una tarea con su fase abierta, aplicar [relevo con fase abierta](../bago5/references/memory-cycle.md#relevo-con-fase-abierta): actualizar y verificar la continuidad en la memoria seleccionada cuando exista autorización vigente; conservar la fase y la tarea en su estado real y comunicar el ID o enlace del recuerdo. Sin autorización o acceso, indicar el bloqueo sin inventar guardado.

Al completar un trabajo, validar el handoff y sus comprobaciones antes de marcar la tarea como realizada en Memoria Viva. Conservar enlaces/rutas de evidencia, agente o responsable, fecha y resultado. Un handoff recibido no basta para cerrar si faltan criterios o evidencia.

Calcular porcentaje de fase = tareas completadas válidamente / total de tareas registradas en esa fase; porcentaje del objetivo = tareas completadas válidamente / total de tareas del objetivo. Mostrar numerador y denominador, y excluir tareas canceladas solo si el modelo canónico las excluye explícitamente. No calcular a partir de peso subjetivo ni contar tareas sin criterio como completadas. Una fase queda completa únicamente al satisfacer su gate; el objetivo, únicamente al satisfacer sus criterios globales y verificaciones.

P0: lectura de fuentes, identidad y estado. P1: contrato, estructura, aceptación, dependencias y lote seguro. P2: ejecutar las tareas autorizadas y registrar evidencias. P3: verificación independiente de criterios y cierre/persistencia. Estas etapas de gobernanza no sustituyen las fases de producto del objetivo.

Una revisión propia no es revisión independiente. No ejecutar /bago-p0-triage ni comandos Pi/Codex si el host no los expone. Si el almacenamiento de memoria, el controlador o la ejecución no están disponibles, declarar con precisión qué parte queda `NOT_RUN` o `BLOCKED`.

## Procedimientos según el encargo

Elige únicamente el procedimiento correspondiente al objeto y al resultado pedido.

- [Organiza objetivos con alcance y aceptación explícitos](../bago5-objetivos/procedimiento.md).
- [Coordina objetivos RC4 con el controlador existente](../bago5-objetivos-rc4/procedimiento.md).
- [Corrige la caducidad de una acción sin cancelar su objetivo](../bago5-recuperacion-objetivo/procedimiento.md).

En Codex, aplica el [formato de respuesta de BAGO](../bago5/SKILL.md#respuestas-en-codex) al comunicar el resultado.
