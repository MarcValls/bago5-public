---
name: bago5-monitor-actividad
description: Consultar actividad efectiva y su historial.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](../bago5/references/controles-especialistas.md#efecto).

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# Monitor de actividad BAGO5

Aplicar [gobernanza](../bago5/SKILL.md) y [seleccion del controlador](../bago5/references/controller-selection.md). Compatible con GPT Classic: comenzar por las herramientas realmente expuestas. No asumir que el directorio de la sesion pertenece a la mision ni inicializar un controlador al consultar. Elegir proyecto y mision; si existen varios destinos sin seleccionar, pedir solo ese dato.

El usuario solicita dos vistas detalladas y separadas. Presentarlas siempre, aunque una no tenga datos. No sumar una declaracion ACTIVE a una lista de procesos vivos. No interpretar ausencia de eventos como inactividad ni una captura antigua como observacion actual.

## Vista 1: misiones, tareas y acciones registradas

Mostrar proyecto, mision, candidata, controlador, estado registrado, objetivo/tareas, agente asignado, STOP/bloqueos, ejecuciones, resultados/errores registrados, ultimos eventos y fecha de actualizacion. Incluir fuente y hora de la lectura. Distinguir tarea administrativa DONE, resultado de una comprobacion, integridad de recibos y aceptacion del producto. Si hay errores, mostrar el estado y la ruta de evidencia disponible; abrir registros solo dentro del proyecto autorizado y cuando haga falta para explicar el error. El lector no valida por si solo hashes de evidencias ni ejecuta comandos de los registros.

Fuentes admitidas: recibos de herramientas de esta conversacion, estado teamctl del proyecto seleccionado o TaskStore Suite explicitamente seleccionado. Los mensajes visibles del chat permiten resumir acciones efectivamente observadas, pero no acreditan un ledger persistente. No leer memorias ajenas para rellenar huecos. No convertir un comando preparado en una accion ejecutada.

## Vista 2: procesos y actividad observada

Mostrar solo procesos/handles expresamente vinculados por el usuario o por una ejecucion observada y autorizada: PID/handle, nombre de ejecutable, hora de inicio, fecha de observacion, ALIVE/EXITED/NOT_FOUND/UNKNOWN, CPU acumulada, memoria residente disponible y cambio entre muestras cuando exista. Un PID coincidente no autentica su pertenencia a una mision. Conservar esta incertidumbre; no atribuir procesos por nombre parecido. PID + instante de creacion distingue instancias; si cambia, no calcular continuidad de CPU.

Los handles nativos pueden consultarse con la herramienta real de espera/estado del host si ya existen. Un estado registrado RUNNING no autoriza afirmar que el proceso vive. Un timeout de observacion no prueba terminacion. No listar todos los procesos ni recolectar lineas de comandos, variables de entorno o contenido de logs sin necesidad y alcance expreso.

## Lector local incluido

[activity_monitor.py](scripts/activity_monitor.py) usa biblioteca estandar Python3.11+. Presenta Markdown por defecto y JSON con --format json. Se ejecuta solo mediante una herramienta real; un conector de carpeta de solo lectura no permite ejecutarlo.

```text
python -B <plugin-root>/skills/bago5-monitor-actividad/scripts/activity_monitor.py --root <proyecto> --controller team
python -B <plugin-root>/skills/bago5-monitor-actividad/scripts/activity_monitor.py --root <proyecto> --controller suite --suite-db <ruta-relativa/control.sqlite3>
python -B <plugin-root>/skills/bago5-monitor-actividad/scripts/activity_monitor.py --root <proyecto> --pid <PID-seleccionado> --format json
```

team lee .bago5-team/runtime/state.json y eventos; Suite exige localizar la base real y pasar --suite-db, sin inventar su ubicacion. La lectura SQLite se hace sobre copia de bytes en memoria. Si hay WAL/journal activo, pedir una instantanea consistente o usar una herramienta de estado existente del controlador; no ignorar el WAL ni presentar una base incompleta como actual. Fuentes mayores de8MiB o modificadas durante lectura se rechazan. Las filas mostradas se acotan a30, hasta200 con --limit; eventos y ejecuciones recientes quedan separados de los totales registrados. Las consultas SQLite tienen limite de instrucciones por tiempo y rechazan vistas/tablas virtuales. El estado y los eventos son capturas separadas y pueden tener instantes distintos.

En Windows se observan procesos mediante consultas del sistema. En otras plataformas solo se informa existencia/acceso cuando es posible; metricas no disponibles quedan explicitas. CPU porcentual exige al menos dos muestras de la misma instancia y se expresa respecto a un nucleo; puede superar100 en procesos multihilo.

Solo si se pide seguimiento, usar --watch-seconds entre0 y60, con --interval entre0.5 y10 segundos. Es una ejecucion acotada y cancelable, no un servicio. No reiniciar automaticamente ni prometer seguimiento cuando termine la herramienta o se cierre el chat. Sin ejecutor, mostrar las acciones visibles de la conversacion y dejar procesos locales NOT_RUN; preparar el comando para el entorno autorizado.

## Formato de respuesta

1. **Actividad registrada:** tabla de tarea/accion, estado, resultado, ultima fecha y evidencia; separar errores y bloqueos observados de lo no evaluado.
2. **Procesos observados:** tabla de PID/handle, instancia, estado observado, CPU/memoria disponibles y hora de comprobacion; marcar vinculo con mision como no verificado si falta prueba.
3. **Limites actuales:** datos ausentes, fuentes desactualizadas, permisos/acceso denegado, campos no soportados y proxima comprobacion util.

No presentar un porcentaje global de progreso sin denominador verificable. No afirmar acceso al razonamiento interno del modelo, a tareas de otros chats o a actividad del sistema no expuesta. Este monitor nunca pausa, reanuda, termina procesos, crea misiones ni escribe memoria por consultar. Esas acciones siguen sus rutas y autorizaciones propias.
