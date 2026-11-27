# BAGO5-CCR-001 · Corrección con recuperación de la conducta válida

## Contenido

- [Regla](#regla)
- [Qué debe conservar una corrección](#qué-debe-conservar-una-corrección)
- [Distinguir causas y desenlaces](#distinguir-causas-y-desenlaces)
- [Ciclo de recuperación](#ciclo-de-recuperación)
- [Integración ejecutable y límites](#integración-ejecutable-y-límites)
- [Interfaz del registro y de la reevaluación](#interfaz-del-registro-y-de-la-reevaluación)
- [Historia, continuidad y datos](#historia-continuidad-y-datos)
- [Aceptación del cambio](#aceptación-del-cambio)

## Regla

Impedir la ejecución incorrecta y conservar la posibilidad de ejecutar la conducta
correcta cuando vuelvan a cumplirse sus condiciones. Mantener el objetivo
legítimo, sus criterios y el trabajo pendiente. Reevaluar la necesidad actual,
las restricciones y la autoridad antes de continuar.

Aplicar esta regla desde [revisión de procedimientos](../../bago5-revision-procedimientos/procedimiento.md),
[control de acciones](../../bago5-control-acciones/SKILL.md), la
[decisión de turno](turn-decision.md) y el
[ciclo de sesión](../../bago5-ganchos-sesion/references/lifecycle.md).
Reutilizar el controlador y el estado de misión existentes.

## Qué debe conservar una corrección

Conservar los siguientes elementos de forma explícita y limitada al alcance:

- Identidad del proyecto, misión, objetivo, revisión, candidata, ámbito y sesión.
- Acción afectada, criterios originales y dependencias pertinentes.
- Conducta observada, causa del bloqueo y fuente que permite contrastarla.
- Conducta correcta que debe seguir disponible y sus condiciones de activación.
- Evidencia de resolución y vínculo con una acción sustituta, cuando corresponda.
- Necesidad actual, vigencia temporal y resultado conocido o incierto del intento anterior.

Una corrección condicionada no se convierte en una prohibición general por
repetición, compactación o relevo. Tampoco se elimina una prohibición vigente
porque se haya resuelto una condición técnica. Conservar la fuente y el ámbito
de cada restricción.

Preservar la conducta válida puede exigir sustituir la acción defectuosa. El
objetivo y los criterios permanecen identificados; el comando anterior no se
reproduce automáticamente. No introducir efectos adicionales bajo el nombre
de recuperación.

## Distinguir causas y desenlaces

| Situación actual | Conducta exigida |
|---|---|
| Falta una condición recuperable | Mantener el paso dependiente pendiente y explicar qué observación permitiría reevaluarlo. |
| La condición vuelve a cumplirse | Resolver ese bloqueo con evidencia actual y reevaluar capacidad, necesidad, dependencias y autorización. |
| La autorización sigue vigente y aplicable | Reutilizarla; no introducir una nueva confirmación rutinaria. |
| Autorización desconocida, caducada o revocada | Mantener la acción bloqueada; la corrección no restaura autoridad. |
| Prohibición vigente | Conservarla hasta una resolución válida de la autoridad competente; cambiar de herramienta no la elude. |
| STOP o revocación de toda la misión | Detener nuevas acciones; la recuperación técnica no reanuda la misión. |
| Resultado de una ejecución incierto | Reconciliar lo sucedido por los canales autorizados antes de repetir el efecto. |
| Orden obsoleta, caducada o sustituida | No ejecutarla; conservar su historia y replantear solo lo que siga dentro del encargo. |
| Criterios del encargo satisfechos | Cerrar; no recuperar operaciones redundantes. |

Un bloqueo acotado no detiene ramas independientes autorizadas. Respetar primero
STOP, PRIVATE, los gates del host y el alcance efectivo de cualquier restricción.
No usar la continuidad para abrir una barrera global ni para solicitar secretos.

## Ciclo de recuperación

1. Identificar la ejecución incorrecta o la condición incumplida y conservar la
   intención válida con sus criterios. Si existe STOP conocido, detenerse sin
   ejecutar este procedimiento ni crear un registro de despedida.
2. Registrar la corrección en el estado de sesión ya autorizado. Mantener una
   regla positiva: qué conducta corresponde y cuándo. La mera anotación de un
   error no justifica invalidar toda una capacidad.
3. Ante un cambio material observado, recuperar el recibo actual y comprobar
   identidad, candidata, ámbito, condiciones, necesidad temporal y resultado del
   intento previo. El paso del tiempo o «hecho» por sí solos no prueban que la
   causa haya desaparecido.
4. Vincular la resolución a la causa concreta. Retirar del recibo actual solo el
   bloqueo resuelto; conservar los demás y mantener el hecho histórico. Si se
   propone otra acción, comprobar que conserva los criterios y que tiene
   autorización aplicable a sus propios efectos.
5. Aplicar `turn_decision.assess` al recibo actual. CONTINUE exige continuar el
   trabajo local autorizado en la sesión activa; CLOSE exige cerrar el encargo;
   BLOCKED conserva pendientes; HANDOFF exige un relevo real; STOP prevalece.
6. Comprobar el resultado y actualizar la evidencia pertinente antes de declarar
   el criterio satisfecho. No confundir la resolución del bloqueo con la
   ejecución o el éxito de la acción.

No repetir una operación fallida ni consumir el turno reevaluando el mismo
evento sin cambios materiales. Correlacionar los eventos y rechazar que un
mismo identificador represente hechos incompatibles. Conservar los conflictos
en lugar de resolverlos borrando historia.

## Integración ejecutable y límites

El [adaptador de recuperación](../scripts/behavior_recovery.py) utiliza el
[contrato de recuperación](behavior-recovery.schema.json) y conserva separado
el recibo `bago5.turn-decision.v1`. Su función es preparar y comprobar una
reevaluación condicionada, reutilizando el evaluador de turno existente.

El registro de corrección pertenece a la sesión y a su continuidad. No es otra
cola, un agente, un planificador ni un almacén de permisos. Los datos declarados
no autentican sus fuentes. El agente y los controles reales del host deben
comprobar los hechos y permisos antes de cada efecto.

Que el adaptador no ejecute herramientas significa que la ejecución corresponde
al agente autorizado. No añade una espera humana cuando el trabajo ya está
autorizado y el resultado actual permite continuar. Una resolución anterior
tampoco concede un permiso reutilizable en otra revisión, candidata o sesión.

Sin ejecución disponible, aplicar estas mismas obligaciones de forma procedural
y distinguir esa aplicación de una prueba del adaptador. Sin agente activo o
mecanismo de eventos disponible, no afirmar que habrá vigilancia ni reanudación
automática en segundo plano.

## Interfaz del registro y de la reevaluación

El adaptador expone funciones puras; ninguna llama a herramientas ni escribe
estado por sí sola:

| Función | Entrada y resultado |
|---|---|
| `register(receipt, spec, now=None)` | Vincular una especificación al recibo actual y devolver el registro de corrección. |
| `reassess(record, receipt, observation, now=None)` | Devolver `record`, `receipt`, `policy_result` y `changed`; conservar la decisión del evaluador compartido. |
| `guard_receipt(receipt, records, now=None)` | Devolver un recibo v1 con las restricciones de corrección que sigan aplicándose. |
| `invalidate(record, source_ref, now=None, *, receipt=None)` | Invalidar la resolución ante un cambio material; si hay recibo, conservar sus referencias de autoridad como historia, sin conceder permiso. |
| `rebind(record, new_receipt, now=None)` | Conservar restricciones del mismo objetivo bajo un binding nuevo, sin transferir resolución ni autorización; la sesión archiva antes el registro anterior. |
| `validate_record(record)` | Comprobar el contrato del registro; datos inválidos generan `RecoveryError`. |

`changed` indica si cambió el registro por una observación nueva; no acredita
progreso, ejecución ni éxito del encargo. El resultado del evaluador es una
decisión de política que el agente debe aplicar mediante los controles reales.

Construir `spec` con `id`, `action_id`, `cause_kind`, `reason`, `source_ref`,
`correct_behavior`, `activation_condition`, `conditions`, `expires_at` y
`prior_execution`. Definir entre una y 32 condiciones, cada una con `id` y
`description`. Usar para
`cause_kind` CONDITION, AUTHORITY, PROHIBITION o UNCERTAIN_RESULT;
`prior_execution` distingue NOT_RUN de UNCERTAIN. Un `expires_at` nulo no
elimina la obligación de comprobar necesidad y vigencia al reevaluar.

Usar `expires_at` únicamente para la caducidad de la orden que se está
evaluando, dentro de sus criterios afectados. Para un impedimento temporal
recuperable, usar normalmente `expires_at:null`; la vigencia de la observación
se expresa en `valid_until`. No declarar OBSOLETE porque falte una condición:
ese estado exige que la orden haya dejado de ser pertinente.

EXPIRED y OBSOLETE no renuevan la orden anterior ni permiten sustituirla
implícitamente dentro del mismo objetivo. La ruta disponible tras su retirada
es una nueva petición explícita con su instancia de objetivo y autoridad
actuales; conservar la orden anterior en el historial. Cambiar identificadores
por conveniencia no constituye esa petición ni levanta restricciones que
sigan aplicándose. La supersesión de una orden terminal dentro del mismo
`goal_id` no está implementada en esta versión.

Si `cause_kind` es PROHIBITION, incluir también `restriction_source_type`:
USER_INSTRUCTION, HOST_PERMISSION o EXPLICIT_APPROVAL. Este campo identifica
la procedencia de la restricción, separada de la autorización de la acción;
es opcional para las demás causas. Una acción autorizada por el usuario puede
estar sujeta a una restricción del host.

Construir `observation` con su propio `id`, `correction_id`, `binding`,
`action_id`, `observed_at`, `valid_until`, `current`, `source_ref`, `conditions`,
`relevance`, `prior_result` y `restriction_resolution`. Identificar cada
condición con `id`, `state` y `source_ref`; conservar SATISFIED, UNSATISFIED y
UNKNOWN como estados distintos. `relevance` distingue NEEDED, OBSOLETE y
UNKNOWN. `prior_result` distingue NOT_RUN, RECONCILED_NOT_EXECUTED,
VERIFIED_COMPLETE y UNCERTAIN. Los tiempos llevan zona horaria.

Para levantar una prohibición, aportar `restriction_resolution` con
`restriction_ref` y `authority` conforme al contrato vigente de autoridad v1.
Una referencia histórica o una condición técnica satisfecha no reemplaza esa
resolución. Su `authority.source_type` debe corresponder a la procedencia
indicada por `restriction_source_type`: HOST_PERMISSION para una restricción
del host; USER_INSTRUCTION y EXPLICIT_APPROVAL pertenecen a la procedencia de
usuario. Esta correspondencia declarada no autentica a la autoridad competente:
el agente y el host deben verificar la procedencia y el alcance reales. Para
las demás situaciones, usar null cuando no corresponda.

El registro distingue WAITING_CONDITIONS, PROHIBITED, RECONCILE, RESOLVED,
OBSOLETE y EXPIRED. RESOLVED describe la causa corregida y su prueba vinculada
al recibo; la decisión puede ser CONTINUE, CLOSE, HANDOFF o BLOCKED según el
estado completo de la misión. Una resolución guardada pierde su eficacia al
vencer la prueba o cambiar el recibo: `guard_receipt` vuelve a exigir una
reevaluación. OBSOLETE y EXPIRED se conservan como estados terminales de ese
registro y no reactivan la orden ante una observación posterior.
STOP pertenece al control de misión y permanece independiente de estos estados.
Una corrección no declara por sí misma un criterio como PASS ni el encargo
como completado.

Al cambiar las condiciones, comprueba la identidad, los permisos y las evidencias actuales. Registra la corrección en la continuidad autorizada del proyecto.

## Historia, continuidad y datos

Conservar el fallo anterior y la observación posterior con su fecha, ámbito y
procedencia. El historial explica la transición. El recibo de turno contiene las
observaciones pertinentes al estado actual; no presentar un FAIL antiguo y un
PASS posterior como si fueran observaciones simultáneas del mismo estado.
Los conflictos actuales siguen siendo conflictos y requieren resolución.

La colección actual de la sesión admite hasta 32 registros de corrección. Cada
registro conserva hasta 64 eventos y 64 invalidaciones; alcanzar el límite
bloquea la ampliación sin borrar historia para liberar espacio. Las instantáneas
`initial_authorization`, `events[].authority_snapshot` y las de
`invalidations[].authority_snapshots` conservan solo `state`,
`source_type` y `source_ref` para recordar denegaciones o revocaciones
observadas. Son metadatos históricos, no permisos ejecutables ni evidencia de
autorización vigente.

La secuencia de eventos e invalidaciones conserva su orden. `events[].assessed_at`
fecha la reevaluación, mientras `observation.observed_at` fecha el hecho
declarado. Esta distinción evita tratar una fecha declarada futura como
evidencia actual.

Al cambiar candidata, ámbito o sesión dentro del mismo proyecto, misión,
objetivo y revisión, `rebind` exige conservar también el objetivo y los
criterios originales. La sesión archiva el registro previo íntegro y crea su
proyección bajo el binding actual, sin resolución heredada. Los estados
terminales se conservan; las demás causas vuelven a requerir comprobación o
reconciliación. `invalidated_authority_refs` conserva hasta 256 referencias
invalidadas para impedir que una denegación o revocación se pierda al cambiar
de ámbito; no contiene permisos. Un resultado previo incierto o completado se
reconcilia con el estado actual antes de repetir efectos. Para otro proyecto
u objetivo, transportar solo historia DATA_ONLY y comprobar la aplicabilidad
antes de registrar una corrección nueva.

En un relevo, transportar los criterios, la regla positiva, causa, resolución
comprobada y pendientes dentro del paquete existente. El destinatario revalida
todo dato necesario para ejecutar; el registro es DATA_ONLY y no transfiere
autenticación ni autorización. No copiar secretos, credenciales, transcripciones
privadas ni razonamiento interno. Persistir solo donde exista autorización y
respetar el ciclo de memoria y sus restricciones.

## Aceptación del cambio

Probar el recorrido completo: bloqueo por causa observada, conservación de
obligaciones, cambio material, reevaluación, continuación correcta o bloqueo
restante y comprobación del resultado. Exigir casos positivos y negativos:

| Caso | Resultado exigido |
|---|---|
| Dependencia ausente y luego disponible | Bloqueo inicial y posterior CONTINUE con autoridad vigente. |
| Recuperación técnica con permiso revocado | Bloqueo conservado; ninguna restauración del permiso. |
| Prohibición y permiso de ejecución con procedencias distintas | Resolución ligada a la procedencia de la restricción; los gates reales siguen vigentes. |
| STOP durante la espera | Ninguna reanudación, comprobación ni escritura de despedida. |
| Acción anterior innecesaria o caducada | Ninguna ejecución diferida de esa orden. |
| Otra acción correcta y autorizada | Sustitución trazable con criterios conservados. |
| Resultado previo incierto | Reconciliación antes de cualquier nuevo intento. |
| Otra rama independiente | Continuación autorizada sin bloqueo global indebido. |
| Evento duplicado o evidencia obsoleta | Ninguna repetición del efecto ni reutilización de prueba vencida. |
| Cambio de identidad, revisión o ámbito | Reevaluación en el nuevo contexto sin heredar autoridad. |
| Cambio de candidata o ámbito del mismo objetivo | Restricciones y referencias invalidadas conservadas, sin reutilizar una resolución anterior. |
| Encargo ya satisfecho | CLOSE sin reactivar trabajo innecesario. |

Informar por separado de pruebas del adaptador, integración de sesión, puente
del runtime y eventos reales de cada host. Una prueba local con entradas
controladas no acredita la activación nativa en Codex, Copilot o Work ni la
ejecución en Windows o en un servicio remoto.
