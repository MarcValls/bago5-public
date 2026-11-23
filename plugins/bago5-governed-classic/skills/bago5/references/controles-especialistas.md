# Controles comunes

<a id="control-1"></a>

## Ciclo de sesión

Aplicar una sola vez por misión el ciclo vigente de [bago5-ganchos-sesion](../../bago5-ciclo-contexto/SKILL.md) y su [contrato de continuidad](../../bago5-ganchos-sesion/references/lifecycle.md); en las derivaciones, reutilizar el binding y estado actuales de proyecto, sesión y memoria. Revisar después únicamente los controles pertinentes al evento y a la tarea, sin reinicializar el ciclo ni recorrer dependencias recursivas. Este enlace no activa todos los especialistas ni autoriza efectos, archivos, persistencia o instalación de hooks; cada operación conserva sus requisitos de alcance, herramientas y autorización vigentes.

<a id="control-2"></a>

## Destino de la operación

Antes de fijar o preparar una versión, runtime o configuración para un destino, o ejecutar una acción que dependa de ellos, aplicar la [comprobación previa del destino](target-preflight.md); si falta evidencia actual, bloquear solo el trabajo dependiente y continuar lo independiente.

<a id="control-3"></a>

## Requisitos del procedimiento 3

Aplicar [bago5](../SKILL.md). Usar las herramientas reales del host y el proyecto seleccionado. Las menciones a .bago aplican solo si ese proyecto usa ese contrato. No depender de Pi, bash ni Codex. Si faltan herramientas, preparar handoff y marcar ejecucion NOT_RUN. Una perspectiva de revision en el mismo agente no es verificacion independiente; declarar el alcance real. No lanzar agentes sin capacidad y autorizacion aplicables.

<a id="control-4"></a>

## Requisitos del procedimiento 4

Aplicar [bago5](../SKILL.md) y [contexto de memoria](memory-scope.md). Este procedimiento recuperado no concede permisos historicos. Resolver proyecto, fuente, runtime y herramientas reales antes de aplicar comandos. Rutas/variables/comandos BAGO son contratos del proyecto original y requieren comprobacion en el destino. No modificar instalaciones, publicar, elevar privilegios ni borrar releases por cargar esta skill. Respetar el alcance ya autorizado; no pedir aprobacion repetida cuando ese alcance ya lo cubre. Sin conector de ejecucion, entregar diagnostico/plan o handoff y declarar ejecucion NOT_RUN.

<a id="control-5"></a>

## Requisitos del procedimiento 5

Aplicar bago5 y su contrato GPT Classic. Las rutas locales y comandos siguientes requieren acceso real al proyecto identificado. No crear ni inicializar la mision ADL de ejemplo por defecto. Usar solo la mision expresamente seleccionada y sus criterios. Si falta teamctl, preparar el trabajo y el handoff con las herramientas disponibles; no afirmar que hubo claim, ledger o validacion del controlador. Los roles son perspectivas de trabajo: solo un agente realmente distinto puede producir verificacion independiente. No lanzar agentes sin autorizacion y capacidad del host.

<a id="control-6"></a>

## Requisitos del procedimiento 6

Aplicar [bago5](../SKILL.md) y su [separacion de memoria](memory-scope.md). Seleccionar el proyecto real antes de usar las referencias. Las rutas, versiones, permisos y bindings historicos del BAGO original son referencias condicionadas a comprobarlos en ese proyecto; no son canon para otro proyecto ni para otros repositorios. Las instrucciones actuales del usuario y del proyecto prevalecen. Los scripts requieren herramientas reales de ejecucion; sin ellas, entregar plan o handoff y marcar ejecucion NOT_RUN. No se presuponen agentes, hooks ni herramientas de Codex en GPT Classic.


<a id="efecto"></a>

## Antes de actuar

Antes de cada efecto comprueba el destino, el permiso vigente y la revisión esperada cuando proceda. STOP o una revocación detiene el efecto afectado. Un cambio de identidad, permiso, revisión o alcance exige reevaluar el siguiente paso. Una respuesta de éxito exige cotejo con la evidencia del destino. Conserva la lectura o el borrador que sigan autorizados.
