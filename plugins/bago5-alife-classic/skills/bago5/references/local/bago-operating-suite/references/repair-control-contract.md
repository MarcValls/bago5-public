# Control de reparación, evidencia y cierre — RC2

## Alcance e integración

`scripts/suite_control.py` amplía la entrada existente `suite_orchestrator.py`
mediante la familia `task`. Es un servicio pasivo: cada transición necesita una
invocación explícita. No crea agentes, descubre tareas nuevas, abre rondas por
su cuenta ni sustituye al orquestador del host.

La implementación usa SQLite y biblioteca estándar. Conserva estado, intentos,
recibos, logs y eventos en una carpeta de tarea separada del candidato. No es un
sandbox del sistema operativo, un emisor de permisos ni una firma de autoría.
Las órdenes ejecutadas conservan los permisos del proceso que invoca la Suite.
La autorización procede del usuario y del host, no del plan JSON.

La API de integración es `add_parser(subparsers)` y `execute(args, context)`.
El contexto proporciona `SKILL` y `candidate_identity`, una función sin
argumentos que devuelve la identidad real del payload instalado. Esta identidad
se guarda exactamente y se vuelve a comprobar antes de admitir trabajo,
reanudar, consumir evidencia o cerrar. `stop` y `status` leen la identidad
registrada: **una avería de integridad no debe impedir registrar STOP**.

## Tres estados independientes

El cierre devuelve `task_status`, `product_status` y `evidence_status`.

| Operación | Condición de cierre de tarea | Estado del producto |
| --- | --- | --- |
| `AUDIT` | Cobertura obligatoria completa, informes válidos consumidos y evaluación terminada | Puede ser `FAIL` si se documentan defectos del producto |
| `VERIFY` | Evaluación obligatoria completa y evidencia válida consumida | Puede ser `FAIL`: una evaluación negativa puede estar terminada |
| `REPAIR` | Todos los checks obligatorios consumidos con resultado `PASS` | Un obligatorio `FAIL`, `NOT_RUN`, `ERROR`, `INTERRUPTED` o `INCONCLUSIVE` bloquea el cierre |
| `PROMOTE` | Los mismos gates de reparación y un `target` explícito | Solo prepara el dictamen; nunca publica ni despliega |

Una auditoría cuyo programa no arranca o termina con error no constituye una
auditoría completada. Para cerrar `AUDIT`/`VERIFY`, cada check obligatorio debe
tener al menos un informe `bago.suite.check-result.v1`, con `coverage=COMPLETE`;
si hay ejecución asociada, debe terminar con código cero y sin interrupción.
Un informe con `status=FAIL` y hallazgos explícitos permite separar el defecto del
producto del correcto funcionamiento del evaluador. Un código cero contradicho
por un informe `FAIL` conserva el resultado negativo del producto.

La cobertura aquí acreditada es la del plan congelado y de sus informes. No se
convierte en una afirmación de cobertura total del repositorio. La corrección
semántica de un auditor o de un test exige su revisión técnica independiente.

La mera presencia de un recibo tampoco cierra la tarea. `consume` lo valida y
registra su consumo; `close` vuelve a validar los bytes y dependencias actuales.
Si la evidencia desaparece o cambia después de consumirla, el cierre se bloquea.

## Plan inicial y candidato congelado

El plan sigue task-plan.schema.json (motor local independiente). Sus
campos son cerrados: no se aceptan campos desconocidos ni identificadores
duplicados. Debe contener la misión, el candidato, la operación, las rutas
exactas, el presupuesto de rondas y los checks con sus dependencias.

```json
{
  "schema": "bago.suite.task.plan.v1",
  "mission_id": "repair-demo-001",
  "candidate_id": "candidate-rc2",
  "operation": "REPAIR",
  "scope": ["candidate.txt"],
  "max_rounds": 2,
  "checks": [
    {
      "id": "verify",
      "kind": "execution",
      "mandatory": true,
      "depends_on": [],
      "artifacts": [
        {"path": "verify_result.json", "schema": "bago.suite.check-result.v1"}
      ]
    }
  ]
}
```

`scope` es una lista explícita de archivos existentes, no un glob ni una búsqueda
recursiva. La Suite guarda el SHA-256 y tamaño de cada archivo, calcula una
identidad conjunta y conserva la identidad del payload ejecutor. Los documentos,
logs o copias de tests que aparezcan después no amplían esta lista ni crean rondas.
Un archivo declarado que cambie o desaparezca invalida ese candidato.
El scope y el payload se vuelven a comprobar al terminar cada hijo, antes de
emitir un recibo válido o un PASS. Si el propio comando cambia el candidato y
sale con código cero, se conserva ese hecho en `process.json`, pero el check
devuelve FAIL/ERROR y no obtiene recibo válido. STOP sigue disponible.

La inicialización se hace sobre el candidato concreto que se desea evaluar.
Para evaluar otros bytes se necesita otro candidato y otra misión explícitos;
no se sustituye silenciosamente el snapshot. El baseline anterior a una
modificación sigue perteneciendo al procedimiento de conservación de la Suite.

El plan admite hasta 10.000 archivos de candidato, 1.000 checks y 100 rondas.
Las dependencias forman un grafo sin ciclos, con profundidad máxima 64. Cada
check de ejecución puede intentarse una vez por ronda; un reintento necesita
abrir otra ronda explícita dentro del presupuesto. No hay reintentos automáticos.

Las rutas de artefactos se declaran por check y deben ser distintas de las rutas
del candidato. Se rechazan rutas absolutas, `..`, alias por mayúsculas, nombres
reservados y enlaces simbólicos/reparse points. Los archivos leídos tienen un
límite de 25 MB cada uno y se comprueba su estabilidad durante la lectura. Estas
comprobaciones no constituyen una instantánea atómica de todo el sistema.

## Comandos

Todos los comandos se ejecutan a través de la entrada de la Suite instalada:

```text
python -B RUTA_SKILL/scripts/suite_orchestrator.py task init --state-dir ESTADO_NUEVO --workspace CANDIDATO --plan plan.json
python -B RUTA_SKILL/scripts/suite_orchestrator.py task round --state-dir ESTADO_NUEVO
python -B RUTA_SKILL/scripts/suite_orchestrator.py task run-check --state-dir ESTADO_NUEVO --check verify --timeout 60 -- python -B verify_candidate.py
python -B RUTA_SKILL/scripts/suite_orchestrator.py task consume --state-dir ESTADO_NUEVO --check verify
python -B RUTA_SKILL/scripts/suite_orchestrator.py task close --state-dir ESTADO_NUEVO
python -B RUTA_SKILL/scripts/suite_orchestrator.py task status --state-dir ESTADO_NUEVO
```

Las rutas son ejemplos; el ejecutable, el candidato y el verificador deben existir
y estar autorizados. `run-check` ejecuta la lista de argumentos que sigue a `--`,
sin un shell implícito, en la raíz `--workspace` registrada. El tiempo máximo
admitido está entre cero y 600 segundos. El verificador concreto debe escribir
los artefactos que declara su check y su propio contenido determina qué afirma.

Un informe estructurado mínimo tiene este contrato:

```json
{
  "schema": "bago.suite.check-result.v1",
  "status": "PASS",
  "findings": [],
  "coverage": "COMPLETE"
}
```

`FAIL` exige al menos un hallazgo. `coverage=PARTIAL` produce un resultado
inconcluso y bloquea el gate obligatorio. El esquema del informe está en
check-result.schema.json (motor local independiente). Un artefacto con
`schema: null` solo tiene validación de existencia, ruta, bytes y tamaño; no se
presenta como contenido validado semánticamente.

Para un check declarado `kind=artifact`, se utiliza `task record-artifact
--state-dir ESTADO --check ID`, seguido de `consume`. Esta ruta no ejecuta un
programa y lo declara. No puede satisfacer un check declarado `kind=execution`.

## STOP, reinicio e interrupción

```text
python -B RUTA_SKILL/scripts/suite_orchestrator.py task stop --state-dir ESTADO --reason "Pausa solicitada"
python -B RUTA_SKILL/scripts/suite_orchestrator.py task status --state-dir ESTADO
python -B RUTA_SKILL/scripts/suite_orchestrator.py task resume --state-dir ESTADO --reason "Continuación explícitamente autorizada"
```

STOP se confirma en SQLite con sincronización completa. Tras confirmarse impide
abrir rondas, asignar trabajo, iniciar acciones, consumir resultados como avance
y cerrar. Un proceso nuevo lee el mismo STOP. Solo `resume` explícito lo levanta;
no restaura el presupuesto de rondas, no lanza acciones y exige que no quede un
hijo propio registrado como `RUNNING`.

La admisión de un hijo y su creación mediante `Popen` comparten la misma
transacción de escritura que serializa STOP. Una petición STOP que llega durante
esa sección espera su registro y después pausa la misión. El supervisor consulta
el control cada 50 ms; solicita terminación y, si hace falta, terminación forzada
del hijo que creó. En POSIX utiliza el grupo de proceso creado para esa ejecución.
El resultado solo afirma terminación cuando observa que ese proceso ha terminado.

Si el ledger falla durante la supervisión, se intenta detener el hijo propio y
se conserva `process.json` fuera de SQLite. Un fallo después de lanzar y antes
de registrar produce `admission_error.json` cuando el almacenamiento permite
escribirlo. Estos registros parciales no satisfacen un gate de verificación.
Si no se confirma la terminación, se conserva `RUNNING/UNINTERRUPTIBLE`; no se
declara una parada efectiva ni se permite reanudar mientras siga sin resolverse.

`task assign --state-dir ESTADO --check ID --worker IDENTIDAD` registra una
asignación externa: **no crea ni contacta a ese agente**. STOP registra para ella
`INTERRUPT_REQUESTED` y `EXTERNAL_UNINTERRUPTIBLE`, con la operación del host
`NOT_RUN`. El pack no puede ejecutar `teamctl` de ADL ni las herramientas privadas
de ChatGPT. Si el host dispone de un mecanismo de interrupción, el orquestador
del host debe invocarlo y conservar su resultado por separado.

Este control se aplica a las operaciones de esta misión que pasan por `task`.
No detiene herramientas externas, acciones realizadas por otro programa ni
procesos desacoplados que hayan abandonado el grupo supervisado. Tampoco prueba
que no queden descendientes de un programa que se daemoniza. Un corte abrupto
del supervisor o del equipo deja el estado conservador sin confirmar; no existe
en esta versión un supervisor independiente ni recuperación automática de ese
proceso. Windows/PowerShell y árboles de procesos Windows requieren aceptación
separada; la evidencia de esta reparación corresponde a las pruebas ejecutadas.

## Validación de recibos y consumo

El contrato es task-receipt.schema.json (motor local independiente).
Un recibo de ejecución vincula:

- Misión, candidato y bytes del payload que controló la acción.
- Check conocido, dependencias exactas y hashes de sus recibos consumidos PASS.
- Un `run_id` que existe en el ledger de procesos realmente lanzados.
- Ejecutable/argumentos, directorio, PID, inicio, fin, código de salida e interrupción.
- Hash y tamaño de stdout, stderr, `process.json` y artefactos requeridos.

Los campos de ejecución se contrastan con el registro creado por el supervisor;
la cadena de un comando aportada en un JSON no constituye ejecución. No se
importa un recibo de otro agente, otra misión o otro candidato como si fuera
una ejecución local comprobada. Los recibos no registrados, con campos extra,
campos ausentes o tipos incorrectos se rechazan. JSON duplicado o no finito se
rechaza al leerlo.

Antes de consumir, se comprueban existencia, bytes, esquema, identidad y
dependencias. Se repite la comprobación antes del cierre, incluso para un recibo
ya consumido. Si falta un artefacto obligatorio, la ejecución y sus logs siguen
registrados, pero el check queda sin evidencia suficiente. Los resultados
parciales, fallidos e interrumpidos no se borran para conseguir un PASS.

La identidad y los hashes son controles locales de coherencia, no autenticación
de un emisor remoto. Un actor con escritura sobre todos los archivos y el ledger
puede alterar ese entorno. La Suite no afirma aislamiento frente a ese actor.

## Reproducción de las comprobaciones

```text
python -B -m unittest discover -s repair-tests -p test_suite_control.py -v
```

Las regresiones emplean procesos reales para la ejecución, la pausa, la
reanudación desde otro proceso y la carrera entre admisión y STOP. Incluyen
inyecciones negativas de fallo del ledger, identidad equivocada, recibo alterado,
artefacto eliminado, esquema incompleto, dependencias no válidas y cobertura
parcial. Son fixtures locales separadas del payload. Las pruebas no demuestran
conexión al host ADL/BAGO5 ni a proveedores externos.


Esta operación necesita el motor local indicado, instalado y autorizado por separado en el equipo del usuario.
