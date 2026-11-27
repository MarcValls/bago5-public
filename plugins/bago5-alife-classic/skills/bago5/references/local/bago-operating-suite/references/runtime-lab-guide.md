# Laboratorio invocable de Spiral y adaptación

Esta capa añade entradas ejecutables a la Suite para las brechas G05 y G06.
Conserva los archivos del runtime reparado RC1, su procedencia y sus contratos.
Los comandos utilizan proyectos de laboratorio nuevos, ligados a una ruta y a
la identidad exacta del candidato. Cada operación del motor empieza en otro
proceso Python y deja su resultado, comando, salida y observaciones en `evidence`.

El laboratorio trabaja con datos controlados: tres valores enteros, 2, 4 y 6,
y un límite de 10. Una tarea construye un resumen con cantidad, suma y resultado
de la comparación. El efecto se escribe por el ExecutionGateway real incluido.
La Suite vuelve a leer el archivo y calcula su resultado de forma independiente.
El radio heurístico de una skill no se usa como prueba del trabajo realizado.

## Entradas de Spiral

Desde la carpeta `skill` de la distribución o desde la skill instalada:

```text
python -B scripts/suite_orchestrator.py spiral init --output /ruta/nueva/lab-spiral
python -B scripts/suite_orchestrator.py spiral run --project /ruta/nueva/lab-spiral
python -B scripts/suite_orchestrator.py spiral inspect --project /ruta/nueva/lab-spiral
python -B scripts/suite_orchestrator.py spiral run --project /ruta/nueva/lab-spiral
python -B scripts/suite_orchestrator.py spiral deactivate --project /ruta/nueva/lab-spiral
```

`init` crea el agente `suite-fixture` por la entrada de ciclo de vida incluida.
`run` ejecuta `BagoAgent` y observa sus doce etapas. Una skill de fixture explícita
conserva el registro nativo de la skill y añade la transformación de datos descrita.
Es un adaptador acotado de tarea; no dota al runtime de ejecución arbitraria de
proyectos. `deactivate` impide nuevas ejecuciones del agente. No interrumpe una
ejecución ya iniciada ni revierte efectos anteriores.

La demostración completa invoca esas mismas operaciones:

```text
python -B scripts/suite_orchestrator.py spiral demo --output /ruta/nueva/demo-spiral
```

Comprueba el efecto y su recibo, el orden de etapas, fase y contador después de
reiniciar, la desactivación, una puerta de armonía cerrada y la negativa del
gateway a escribir fuera de la raíz autorizada. Un caso adicional coloca una
obstrucción real en el almacenamiento del fixture para comprobar que no se
declara una inicialización correcta. Esa obstrucción está preparada expresamente
para la prueba y no describe una avería encontrada en el equipo del usuario.

## Entradas de adaptación

```text
python -B scripts/suite_orchestrator.py adaptation init --output /ruta/nueva/lab-on --mode on
python -B scripts/suite_orchestrator.py adaptation cycle --project /ruta/nueva/lab-on
python -B scripts/suite_orchestrator.py adaptation inspect --project /ruta/nueva/lab-on
```

Cada `cycle` llama al `plan`, `act` y `observe` reales del loop incluido. Los únicos
adaptadores de herramienta disponibles son `health` y `dashboard`, y operan sobre
el fixture. El primero detecta que la suma supera el límite, genera el resultado
y devuelve fallo de validación de datos. El segundo genera el resumen de control.
La observación del loop registra el resultado verdadero: un intento fallido no
se transforma en un éxito de aprendizaje.

Después de tres fallos observados de `quick_check`, un proceso nuevo conserva
la información y su plan omite ese objetivo. `act` respeta la omisión y no llama
a la herramienta correspondiente. El objetivo de control `summary` sigue activo.
Con `--mode off`, el mismo fixture se ejecuta pero no se registran observaciones
de aprendizaje ni se aplica esa exclusión.

```text
python -B scripts/suite_orchestrator.py adaptation demo --output /ruta/nueva/demo-adaptation
```

La demostración compara cuatro ciclos por modo, con los mismos datos y candidato.
Reinicia el proceso en cada ciclo, observa tres efectos de `health` en modo `on`
y cuatro en modo `off`, y comprueba que otro proyecto no hereda la exclusión.
También rechaza una observación de tipo inválido y hace visible una imposibilidad
controlada de persistir. Se conservan los casos negativos como `FAIL` esperado;
el informe global solo pasa cuando se observa la negativa concreta prevista.

## Evidencia y alcance

`DEMO_EVIDENCE.json` enumera las comprobaciones y enlaza los resultados por
operación. Cada resultado incluye identidad del candidato, huellas de adaptador,
worker, lock y procedencia del runtime, código de salida, salida bruta y lectura
independiente de los efectos. Una discrepancia del candidato durante la ejecución
impide `PASS`. Un laboratorio copiado a otra ruta debe inicializarse de nuevo:
no se reasigna silenciosamente su identidad de proyecto.

`PASS` de `adaptation cycle` significa que el recorrido y su evidencia se han
producido correctamente. Dentro de ese resultado, `quick_check` puede y debe
conservar `success: false` cuando los datos incumplen el límite. Son dos niveles
distintos de resultado.

La prueba demuestra una regla persistida de exclusión después de fallos repetidos.
No demuestra optimización general, empatía, mejora sostenida, entrenamiento BC ni
una evaluación independiente con tareas de usuario. Tampoco ejecuta la CLI heredada
completa, proveedores externos, agentes nativos del host o una integración BAGO5/ADL.
La evidencia en Linux no verifica Windows, PowerShell o NTFS.

Un fallo del runtime puede dejar efectos parciales: no existe aquí una transacción
única de todos sus archivos ni una garantía de replay después de un corte. La
supervisión y parada de trabajos de la Suite se describen en su propia capa de
control. El marcador del laboratorio y los hashes son controles locales de
identidad y alcance; no son una firma de editor ni un aislamiento del sistema
operativo.


Esta operación necesita el motor local indicado, instalado y autorizado por separado en el equipo del usuario.
