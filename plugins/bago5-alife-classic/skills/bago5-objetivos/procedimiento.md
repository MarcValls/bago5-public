[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# $bago-goal · Misión finita

Al recibir `$bago-goal <objetivo>`: identificar proyecto, objetivo, alcance, criterios de aceptación, candidata, fuentes, capacidad/herramientas y permiso. Recuperar las misiones relacionadas del proyecto identificado y distinguir metas activas, detenidas y cerradas; no mezclar otros proyectos.

Proponer o ejecutar (si autorizado) la mínima secuencia necesaria, con checkpoints, pruebas y evidencias. Si el usuario pide `/goal resume`, recuperar las metas pendientes desde fuentes reales; si no existe TaskStore, declararlo y no inventar estado o continuidad autónoma.

En misiones de varios pasos, aplicar [autonomía y recuperación](../bago5/references/autonomia-recuperacion.md): mantener objetivos con criterios observables, dependencias, estado, evidencia y siguiente acción; continuar trabajo independiente autorizado ante un bloqueo. Un objetivo ejecutado no es completo hasta cumplir sus criterios y comprobaciones. Un checkpoint conversacional o un handoff no constituye por sí mismo almacenamiento duradero ni autoridad para reanudar.

## Objetivo y plan en Memoria Viva

Cuando el proyecto tenga una Memoria Viva autorizada y la intención incluya organizar o ejecutar un plan, recuperar primero el objetivo y el plan literal vigente. Distinguir objetivo (resultado), plan (procedimiento completo y versionado), fase (etapa del plan) y trabajo (unidad verificable). Aplicar la skill `memoria-viva-plan-fase` si está disponible y comprobar el esquema real antes de escribir; no crear una pantalla ni un registro paralelo.

En el backend legado, `goal.plans[]` contiene fases v1, no planes padre independientes. Conservar y editar solo las fases existentes mediante sus IDs y versión esperada recuperados, según el contrato del servicio. No convertir un plan nuevo en una fase para lograr guardarlo, ni afirmar que un contrato v2 propuesto está desplegado. Si faltan API o persistencia v2, mantener el plan nuevo como borrador preparado y su guardado `NOT_RUN`; conservar el plan literal ya recuperado y el vínculo con su objetivo. No reconstruir un plan ausente concatenando fases: declarar `NO_RECUPERADO`.

Secuencia obligatoria para planificar y distribuir:

Antes de iniciar o reanudar cada fase, completar el [preflight de fase](../bago5-plan-por-fases/references/phase-preflight.md), incluidas herramientas, accesos, permisos y capacidad de ejecución, verificación y entrega. La lectura del objetivo y del plan permite inspeccionar; seleccionar recursos, materializar asignaciones o modificar requiere GO vigente o un paso expresamente autorizado de preparación mediante `can_prepare`, conservando el gate humano pendiente. No omitir la comprobación por invocar esta habilidad directamente ni por haber superado una fase anterior. Anunciar antes el host necesario y toda intervención humana pendiente; continuar sin nueva confirmación cuando el preflight habilite el tramo y la autorización siga vigente.

1. Leer el objetivo y plan existentes, versión, estado, dependencias, historial y tareas. Preservar el texto literal y distinguir contenido heredado, confirmado y aún no comprobado.
2. Si falta objetivo, resultado esperado o criterio material, mantener el plan como borrador y pedir el dato esencial; no convertir una lista de fases en objetivo inventado. No sustituir planes existentes sin autorización.
3. Registrar/actualizar únicamente entidades que soporte el esquema comprobado y cuya edición esté autorizada. Conservar IDs, texto literal, versiones e historial; no duplicar el objetivo o el plan para facilitar la asignación. Cada trabajo preparado debe enlazar objetivo, plan/version y fase, describir resultado, estado, dependencias, criterio de cierre y evidencia esperada. Distinguir IDs propuestos de IDs persistidos. En v1 no introducir campos, planes padre ni dependencias entre trabajos de fases distintas que el contrato no admita.
4. Comprobar que cada tarea pertenece a una sola fase, que las dependencias apuntan a trabajos existentes y no generan ciclos, y que los gates/criterios de fase y objetivo son observables. Marcar lo desconocido como pendiente; no inferir que una fase está completa por su posición o por una narración resumida.
5. Solo después de leer de vuelta y confirmar la estructura admitida y persistida, derivar de cada tarea el work item ejecutable del controlador compatible. La identidad del trabajo debe enlazar al mismo objetivo, plan/version cuando exista, fase y tarea; no duplicar el ledger. Los preparativos independientes autorizados pueden continuar sin inventar IDs, persistencia, claims o ejecución del plan.
6. Al recibir resultados, registrar evidencia y estado en la misma tarea/fase del objetivo. Actualizar porcentajes desde el número de trabajos cerrados respecto al total definido, y la fase/objetivo solo cuando su gate se cumpla. No contar propuestas, asignaciones ni texto de handoff como trabajo completado.

Si el servicio de memoria no está disponible o su esquema no admite la estructura, preparar la propuesta en la conversación, indicar `NOT_RUN` para la persistencia afectada y no distribuir trabajo dependiente de IDs/estado no confirmados. Una lectura de regreso acredita que los datos son recuperables; no acredita por sí sola la corrección del contenido. Para dividir responsabilidades y pases sin cambiar el plan fuente, aplicar [plan agéntico portable](../bago5-plan-por-fases/references/agentic-plan.md).

`STOP` mantiene el bloqueo hasta reanudación expresa. Actualizar fuentes o misiones persistentes requiere permiso y operación verificable. Antes de la entrega, aplicar la [decisión de turno](../bago5/references/turn-decision.md): si queda un paso local elegible, ejecutarlo; si los criterios del encargo están satisfechos, cerrar sin inventar una siguiente tarea. Conservar los criterios originales y la procedencia de sus pruebas al integrar resultados. Entregar bloqueos o relevo solo cuando correspondan a un impedimento o cambio de entorno real.

Antes de inicializar estado, aplicar [seleccion exclusiva del controlador](../bago5/references/controller-selection.md).

Para un contrato de objetivo en archivos autorizados, usar [plantilla](assets/goal-template.md). Sustituir todos los ejemplos de gates npm por los comandos reales del proyecto; no ejecutarlos por aparecer en la plantilla. Conservar la identidad del objetivo y versionar cambios de alcance/criterios, sin reescribir historia. .goals y .bago/goals son variantes históricas: elegir solo la ruta vigente del proyecto y no crear ambos registros. Aclarar solo criterios materialmente desconocidos; no repetir una entrevista ya resuelta.
