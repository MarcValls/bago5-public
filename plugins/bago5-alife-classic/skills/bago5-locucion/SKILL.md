---
name: bago5-locucion
description: Producir una locución a partir de un texto.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](../bago5/references/controles-especialistas.md#efecto).

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# BAGO5-LOCUTION · VOZ LOCAL / Kokoro

Usa esta skill cuando el usuario pida leer en voz alta, locutar, convertir texto a voz o escuchar una respuesta mediante la aplicación VOZ LOCAL que acompaña BAGO5_ADL.

## Capacidad y límites

La fuente conocida es el paquete `user_inputs/VOZ_LOCAL_RECEPTOR_KOKORO_v1.3.1` de BAGO5_ADL; su README identifica la aplicación como v1.3.2. Es una app local e independiente con Kokoro, voces `alex` (predeterminada), `dora` y `santa`, y receptor HTTP autenticado en `127.0.0.1:8765`. El plugin aporta enrutamiento y procedimiento; **no instala la aplicación, no inicia un proceso residente, no lee conversaciones automáticamente y no crea por sí solo una herramienta de voz**.

Antes de enviar:

1. Comprueba las herramientas reales de esta sesión. Solo usa una herramienta de ejecución que pueda llegar al mismo equipo donde corre VOZ LOCAL. Una skill, una ruta de archivo, un conector de lectura o la presencia de la app no prueban esa capacidad.
2. Si el usuario pidió locutar el texto, usa ese texto sin alterarlo, salvo que pida edición. No incluyas contexto privado ajeno al texto solicitado.
3. Localiza el paquete por una ruta configurada o confirmada en el host. No supongas que existe en `D:` ni uses la carpeta de fuentes/MCP si no es la misma instalación que ejecuta VOZ LOCAL.
4. Comprueba que `voz_local.py` y `.venv\Scripts\python.exe` existen. No instales dependencias, descargues modelos ni arranques la app/receptor en segundo plano sin petición explícita.
5. Comprueba que el puerto pertenece al receptor VOZ LOCAL. Si responde una app desconocida, hay conflicto o no se puede identificar el proceso, detente; no lo cierres, reemplaces ni adoptes.

## Ejecución en un host local autorizado

Con el receptor iniciado por el usuario desde la propia interfaz VOZ LOCAL (modo **Receptor HTTP**) o mediante su lanzador documentado, el cliente oficial del paquete puede enviar el texto y esperar su recibo de estado. Desde PowerShell, con la ruta real del paquete ya resuelta:

```powershell
$vozRoot = '<ruta confirmada del paquete VOZ LOCAL>'
$python = Join-Path $vozRoot '.venv\Scripts\python.exe'
$cli = Join-Path $vozRoot 'voz_local.py'
if (-not (Test-Path -LiteralPath $python) -or -not (Test-Path -LiteralPath $cli)) { throw 'Paquete VOZ LOCAL incompleto' }
& $python $cli enviar $texto --voz alex --esperar
```

Sustituye `$texto` por el texto exacto que el usuario pidió locutar. Usa `--voz dora` o `--voz santa` solo si el usuario lo elige. Conserva la autenticación gestionada por el propio cliente; nunca leas, muestres, copies ni registres `.voz_local_token` en la conversación o en logs. No expongas el receptor fuera de `127.0.0.1`.

El cliente `enviar --esperar` es la ruta preferida porque usa el token local y el protocolo del paquete. Si la única ruta disponible es una llamada HTTP directa, requiere `POST /speak` con `X-Voz-Token` y JSON `{ "text": "…", "voice": "alex", "speed": 0.98 }`; no imprimas el token. Un `202 RECEIVED` confirma aceptación en cola, no reproducción. Si se consulta estado, informa exactamente el estado devuelto; `PLAYBACK_RETURNED` acredita que el método de reproducción retornó, no que una persona oyera el audio.

## Si el host no puede ejecutar la ruta local

No afirmes que el audio se produjo. Indica `NOT_RUN` y el bloqueo observable (p. ej. no hay ejecución local, paquete no localizado o receptor no activo). Ofrece una instrucción concreta para que el usuario abra VOZ LOCAL → **Receptor HTTP** y después habilite el ejecutor local compatible, o entregue el texto como archivo/entrada si lo prefiere. No sustituyas Kokoro por un servicio de voz en la nube sin elección expresa.

## Privacidad y cierre

La aplicación documenta generación local y envío por loopback; el texto no se guarda en disco por el receptor y los WAV temporales se eliminan al terminar la reproducción. Mantén esa frontera: no envíes audio/texto a Ollama u otro servicio, no guardes WAV, y no actives micrófono/dictado salvo solicitud separada. Informa por separado de `PREPARED`, `EXECUTED`, estado recibido y reproducción; nunca infieras que el usuario oyó el audio.

En Codex, aplica el [formato de respuesta de BAGO](../bago5/SKILL.md#respuestas-en-codex) al comunicar el resultado.
