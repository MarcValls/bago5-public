# BAGO-SCR-001 · contrato acotado

Objetivo: facilitar el reconocimiento de contexto al inicio de una sesión de
Codex CLI sin inicializar el proyecto ni aceptar automáticamente sus afirmaciones.

## Entrada y selección del proyecto

Una entrada JSON en stdin, máximo 65.536 bytes. Solo se atiende `SessionStart` y
los cinco valores de `source` documentados. Otros eventos producen `{}`. Entradas
inválidas devuelven un diagnóstico constante, sin volcar el texto recibido.

`cwd` debe ser absoluto y señalar un directorio existente. Se usa exclusivamente
esa ubicación; no se consulta el cwd del proceso como sustituto, git, padres,
hermanos, transcripciones, homes ni configuración global. Solo se examinan los
componentes de ruta mediante metadatos para detectar enlaces o reparse points.

Marcadores directos: `.git` o `.bago/CONTEXT_STRUCTURE.json`. Son indicios, no
autenticación ni confirmación del proyecto. Sin ellos: `ROOT_UNCONFIRMED`.
Con ellos: `UNCONFIRMED_CWD_CANDIDATE`, incluso si la estructura es válida.
El agente mantiene la obligación de confirmar la raíz antes del bootstrap.

## Inventario

1. Verificar SHA-256 de la estructura canónica incluida.
2. Si existe la estructura local, leerla y comprobar su compatibilidad exacta
   con la versión 1.0.0; admitir adaptaciones de rutas/flags y `extensions`.
3. Validar todas las rutas antes de abrir los archivos de contexto.
4. Leer como máximo 1 MB por archivo habilitado; calcular identidad y comprobar
   UTF-8 y, cuando corresponde, JSON objeto. No evaluar la verdad de sus afirmaciones.
5. Omitir el contenido de los archivos deshabilitados.
6. Emitir como máximo 6.000 caracteres en `additionalContext`, usando códigos
   constantes para errores y JSON escapado para los metadatos.

La presencia nunca pasa a `REVIEWED`, `VERIFIED` o `AUTHORIZED`. La lectura de bytes
para hash/sintaxis no sustituye la lectura semántica completa por el agente.
Ninguna fecha, flag o declaración de revisión del proyecto constituye autorización.

## Efectos y fallos

El hook no contiene operaciones de escritura, llamadas de red, ejecución de
procesos, importación de código del proyecto o invocación de `init`.
Se excluyen de la afirmación de solo lectura los preparativos de las fixtures,
la extracción del paquete, la edición explícita de la configuración del host,
los metadatos de acceso del sistema de archivos y los registros propios de Codex.

Los errores cierran la admisión de contexto, pero se devuelve código 0 con
diagnóstico para no bloquear el trabajo de Codex. Esto no es un mecanismo de
autorización ni una barrera contra escrituras. El tiempo del hook está acotado
por la configuración del host; un fallo del intérprete queda fuera del handler.

## Criterios de aceptación

- Entrada/salida verificadas por proceso real con eventos etiquetados como sintéticos.
- Archivo existente preservado; ausentes siguen ausentes; sin nuevos directorios.
- JSON inválido, versión desconocida, modificación de políticas, enlaces y escape
  de ruta no se aceptan como contexto válido.
- Contenido del documento, transcripción y archivos ajenos no aparecen en la salida.
- Comando CLI generado sin dependencias de un plugin; solo imprime configuración.
- Original ZIP y estructura canónica conservan SHA-256.
- Para marcar integración con CLI como verificada: observación real de `/hooks`,
  confianza, ejecución, `cwd` y fuentes de evento en el host objetivo.

La aceptación local permite entregar el prototipo. La ausencia de la última
evidencia impide afirmar activación o funcionamiento verificado en la CLI del usuario.


Esta operación necesita el motor local indicado, instalado y autorizado por separado en el equipo del usuario.
