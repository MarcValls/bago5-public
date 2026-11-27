# BAGO SessionStart CLI · solo lectura · 0.1.0-RC1

Complemento independiente para **Codex CLI**, basado en la estructura de contexto
del ZIP `BAGO5os_1.4.5_RELAY-RC1_CONTEXT-BOOTSTRAP.zip` facilitado por Marc.
No modifica ni sustituye esa distribución o ninguna skill instalada.

Al recibir `SessionStart`, examina exclusivamente el `cwd` recibido. Si allí hay
`.git` o `.bago/CONTEXT_STRUCTURE.json`, informa de la estructura y de los tres
archivos de contexto: presentes, ausentes, deshabilitados o pendientes de revisión.
La raíz sigue siendo candidata. Nunca asciende a otro proyecto para completar el inventario.

El hook emite metadatos en `hookSpecificOutput.additionalContext`: rutas, tamaños,
SHA-256 y estados. No incluye cuerpos, plantillas, instrucciones del proyecto,
transcripciones ni valores de `extensions`. Todos los documentos presentes
quedan pendientes de revisión semántica; un hash no acredita vigencia ni autorización.

## Estado alcanzado

- **IMPLEMENTADO:** hook, validación de estructura, propuesta de configuración CLI,
  demostración reproducible y pruebas positivas/negativas.
- **VERIFICADO LOCALMENTE:** 28 pruebas en Linux/Python 3.12 y demostración con
  evento sintético. Evidencia y huellas del candidato en `evidence/`.
- **NOT_RUN:** Codex CLI real, Windows/PowerShell, revisión de confianza mediante
  `/hooks`, recepción real de `cwd` y eventos del host.
- **PROPUESTO:** agrupación futura de skills en un plugin; barrera `PreToolUse`;
  interfaz/MCP. No forman parte de este prototipo.

## Probar sin instalar

Requisito: Python 3.10 o superior; solo biblioteca estándar, sin dependencias pip.
Extrae el ZIP y entra en la carpeta `bago-session-context-readonly`.

En PowerShell:

```powershell
python -B -I scripts/demo.py
python -B -I -m unittest discover -s tests -v
```

Si Python se invoca con el lanzador de Windows, usa `py -3` en lugar de `python`.
`DEMO.ps1` también detecta ambos nombres. La demo crea un proyecto sintético en
una carpeta temporal, invoca el hook mediante stdin/stdout, compara sus archivos
y elimina la carpeta al terminar. La demo prepara la fixture; el hook solo la lee.

Resultado esperado: `result: PASS`, `unchanged: true`, `event_origin: SYNTHETIC`
y `codex_cli: NOT_RUN`. No confundir esta demo con una sesión real de Codex.

## Preparar la configuración de Codex CLI

Desde esa misma carpeta, genera la propuesta para **tu propio sistema**:

```powershell
python -B -I scripts/print_cli_config.py
```

El comando solo imprime JSON. Construye una ruta absoluta al hook desde la
ubicación real del paquete, sin depender de `PLUGIN_ROOT`. No escribe configuración
ni confía en el hook. Mantén el paquete en una ubicación estable; si lo mueves,
regenera y revisa la definición.

Para la primera prueba, incorpora ese JSON al archivo `.codex/hooks.json` del
proyecto confirmado. Si ya existe, conserva todas sus entradas y añade únicamente
el grupo `SessionStart`; no sustituyas el archivo entero. Evita duplicarlo en
`config.toml` o en otra capa, porque los hooks coincidentes se acumulan.
La configuración global `~/.codex/hooks.json` queda como opción posterior.

Desde la raíz confirmada del proyecto:

```powershell
codex --version
codex
```

Dentro de Codex CLI, abre `/hooks`, inspecciona la definición y el script y confía
en esa definición si es correcta. La documentación oficial exige esa revisión
para hooks no administrados; no se activa ni elude desde este paquete.
La capa `.codex` del proyecto también debe ser de confianza para que se cargue.
Después de confiar en el hook, inicia una sesión nueva para comprobar `startup`.
Si tu versión no reconoce estas funciones, registra la versión y el error;
el prototipo no puede suplir una capacidad ausente del host.

## Primera comprobación real

Pide a Codex que muestre el `cwd`, `source`, `root_binding`, `status` y los estados
de archivos del inventario recibido por `SessionStart`, sin inicializar contexto.
Comprueba que el `cwd` coincide con la carpeta desde la que abriste la CLI.
Conserva la salida del hook y la versión de Codex; un texto del modelo sin salida
de hook no demuestra que el hook se haya ejecutado.

Repite en reanudación, bifurcación y compactación usando las operaciones disponibles
en tu versión. Registra el `source` realmente recibido. Comprueba también `clear`
cuando el host lo exponga. Si una operación no existe o no puede observarse,
regístrala `NOT_RUN`; no la deduzcas de una prueba sintética.

Abrir una carpeta o cambiar de directorio no constituye por sí solo un evento
`SessionStart`. Si arrancas en una subcarpeta sin marcador propio, el resultado
esperado es `ROOT_UNCONFIRMED`; inicia una sesión desde la raíz confirmada.

## Estados

- `ROOT_UNCONFIRMED`: no hay marcador directo; no se ha leído contexto de carpetas superiores.
- `CONTEXT_MISSING`: hay marcador, pero faltan los archivos habilitados.
- `REVIEW_REQUIRED`: hay archivos presentes o un problema que requiere revisión.
- `ALL_DISABLED`: la estructura válida deshabilita los tres artefactos.
- `INSPECTION_BLOCKED`: entrada, estructura o ruta no admisible; no se acepta contexto.
- `OUTPUT_LIMIT_REVIEW_REQUIRED`: el inventario excedería el límite; se devuelve un diagnóstico.

`INSPECTION_BLOCKED` bloquea la inspección, **no la sesión ni las herramientas de Codex**.
El hook siempre es informativo. No implementa `PreToolUse` ni concede permisos.

## Conservación y límites

La estructura canónica incluida es una copia idéntica de la del paquete original.
Las rutas y flags `enabled` pueden adaptarse, conforme al contrato original.
IDs, formatos, políticas y plantillas deben conservarse. `extensions` puede contener
datos de proyecto, pero no participa en permisos o revisión y no se inyecta.

El hook no crea ni cambia el contenido de archivos, no ejecuta comandos externos,
no usa red ni importa módulos del proyecto. `-B -I` evita bytecode y aísla las
importaciones de Python del directorio de trabajo. La lectura puede actualizar
metadatos de acceso del sistema de archivos; el propio host puede guardar su
historial de hooks. No se promete que todo el proceso Codex sea de solo lectura.

Se rechazan enlaces simbólicos/reparse points observables, rutas de escape,
colisiones de mayúsculas/minúsculas y archivos no regulares. La inspección no
es un sandbox frente a cambios concurrentes hostiles en directorios, ni evita
que otra herramienta o proceso modifique el proyecto después.

Consulta `CONTRATO.md`, `CONTINUIDAD.md` y `evidence/REPORT.json` para el alcance exacto.

## Fuentes oficiales consultadas · 29 de octubre de 2026

- [Hooks: entradas, eventos, salida, configuración y confianza](https://learn.chatgpt.com/docs/hooks)
- [Plugins: empaquetado opcional y confianza de hooks](https://developers.openai.com/plugins/build/plugins)

El contrato de hooks documenta `startup`, `resume`, `clear`, `compact` y `fork`,
la entrada JSON por stdin, `cwd` y la salida `additionalContext`. No documenta
un evento específico de abrir carpeta. La configuración directa de CLI evita
requerir un plugin para esta primera prueba.


Esta operación necesita el motor local indicado, instalado y autorizado por separado en el equipo del usuario.
