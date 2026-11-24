# BAGO5 · PROTOCOLO DE PACKS DE VERSIONES Y CIERRE DE DESCARGAS v0.1

## Decisión recuperada y diagnóstico de por qué no actuaba

El protocolo previo de entregas ya existía **parcialmente** en `skills/bago5/references/entrega-guiada.md`: batería inicial, `.cmd → .ps1`, LEEME, hashes, verificación y paso siguiente. **Faltaba una instrucción universal y explícita sobre posición de descargas, ZIP acumulativo con todas las versiones disponibles y destino/comparación de versiones**. Además el procedimiento anterior se activaba para scripts/procesos, no para cualquier artefacto compuesto. Esta especialidad amplía esa carencia sin reemplazar skills previas.

## Contrato de un pack acumulativo

`<PRODUCTO>_VERSION_PACK_vN.zip` (o equivalente validado; no renombrar artefactos ya distribuidos).

Contenido mínimo del ZIP del pack:

- `LEEME.md`: objetivo, condiciones, fuentes, Windows/Linux si aplica, primer paso, instalación sin sobrescrituras silenciosas, limitaciones y STOP.
- `VERSIONES.md`: tabla con todas las versiones realmente disponibles, tipo (baseline, incremental, runtime privado, docs), posición real dentro del ZIP, SHA, vigencia/estado y relación parent→child; faltantes como `NO_RECUPERADO` fuera de la lista de incluidos.
- `INVENTARIO.json` o manifiesto tipado: cada ruta completa de miembro del pack, tamaño y hash; presencia efectiva; tipo.
- `SHA256SUMS.txt`: hashes exactos de archivos de payload y de los documentos de control pertinentes; no autofirmar el propio SHA256SUMS.
- `versiones/<id>/`: copia íntegra de cada versión realmente recuperada; conservar nombres y bytes originales; no extraer y mezclar en un único runtime por defecto.
- `evidence/` y `scripts/` cuando correspondan; evidencias vinculadas por versión, logs de pruebas, comandos, entorno, PASS/FAIL/NOT_RUN.

Un ZIP anterior de versiones también puede estar incluido como artefacto histórico, pero no sustituye la enumeración efectiva de versiones disponibles: evitar pack anidado como única forma de localizar ficheros si hay espacio para entrega directa.

## Carpeta de destino

La instrucción de destino se expresa de forma ejecutable: `descargar en <RUTA_SUGERIDA>` y `extraer en <CARPETA_NUEVA>`, nunca `sobrescribir todo`. Ejemplo Windows (ruta relativa, no inventada):

- Descarga: `<RAÍZ_DEL_PROYECTO>\entregas\<PRODUCTO>\descargas\`.
- Extracción: `<RAÍZ_DEL_PROYECTO>\entregas\<PRODUCTO>\PACK_vN\`.
- Instalación: **NO INFERIDA**. Solo dar ruta real si fue comprobada. Si el ZIP es código para ejecutar, especificar qué versión base conserva y qué rutas/archivos reemplaza, con backup/rollback y prueba diferencial si procede.

Si es una versión superior, separar **nueva entrega acumulativa** de **nueva versión del software**. Un PACK_v2 no demuestra una app v2. Nunca recomendar copiar una versión de desarrollo encima de un despliegue en uso.

## Máximo de tamaño

Cuando se alcance tamaño límite del entorno, cerrar PACK_vN con su inventario y empezar PACK_v(N+1). Ambos son acumulación lógica: el índice del segundo declara qué conserva y dónde se recupera el anterior. No declarar que contiene archivos omitidos. Pedir la fuente faltante solo si no se puede recuperar.

## Entrega al usuario

El bloque `DESCARGAS Y UBICACIÓN` es la **última sección de la respuesta**. Antes de él vienen resultados, pruebas, fuentes, limitaciones y `NOTA FINAL`; tras el último enlace no se redacta texto. Si el formato del usuario prohíbe encabezados/bloques de texto adicionales, prevalece su solicitud y se entrega sin esos rótulos. Priorizar un solo pack completo y no dispersar todos sus miembros en varios enlaces.

## Control antirregresión

Invariantes: preservar SKILL BAGO5-govern, rutas existentes, defaultPrompt íntegro, configuración de apps, baselines, scripts y versiones. La skill instalada no acredita por sí sola que el host la haya invocado; probar actualización del plugin, inventario completo, ruta activable y una entrega real de archivos antes de declarar `VALIDATED`. Una comprobación local de estructura es `PASS_ESTATICO`, comportamiento en ChatGPT/Codex `NOT_RUN` hasta ensayo real.
