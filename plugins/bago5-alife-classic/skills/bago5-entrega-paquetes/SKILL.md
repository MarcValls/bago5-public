---
name: bago5-entrega-paquetes
description: Construir una entrega instalable con identidad verificable.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](../bago5/references/controles-especialistas.md#efecto).

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# BAGO5 · Entrega de artefactos, versiones y enlaces

## Activación

**Se aplica a TODA respuesta de trabajo gobernado que entregue uno o varios archivos descargables**, aunque no se hayan pedido scripts: ZIP, parches, código, versiones, pruebas, documentos, evidencias, esquemas, paquetes o resultados compuestos. También aplica si una tarea produce varios archivos en una sola operación. No obliga a fabricar archivos para contestar una consulta.

Este especialista complementa el procedimiento ya instalado en `skills/bago5/references/entrega-guiada.md` y no sustituye el coordinador ni sus permisos. Para ZIP con scripts en Windows conserva batería completa, LEEME, SHA256SUMS y lanzadores `.cmd` → `.ps1` relativos. Para paquetes de versiones consulta [protocolo](references/PROTOCOLO_VERSIONES_Y_ENLACES.md) y [vectores](references/ACCEPTANCE.json).

## Paquete para un relevo CHAT, WORK o CODEX

Cuando el destinatario necesite artefactos para la siguiente acción, entregar un único ZIP completo para ese alcance. Incluir `LEEME`, el prompt literal exacto comprobado en la memoria autorizada del proyecto cuando su guardado se haya solicitado, inventario, hashes, evidencias y los fuentes/contratos/scripts de arranque realmente necesarios. Referenciar en LEEME el ID y versión del registro del prompt sin alterar su texto. Comprobar que el prompt mostrado, el recuperado y el archivo incluido coinciden; si el guardado falla, informar el estado real y no declarar el relevo completo.

Presentar la acción como `CODEX — Siguiente acción: ...`, `WORK — Siguiente acción: ...` o `CHAT — Siguiente acción: ...` antes de explicar el trabajo. No incluir secretos ni transferir permisos. Inventariar límites y dependencias externas comprobadas; un paquete incompleto debe identificarse como tal, sin afirmar que incluye fuentes no recuperadas. No fabricar un ZIP vacío ni comprimir solo el prompt para aparentar una entrega de fuentes. Si no hay artefactos necesarios, entregar el prompt y su referencia de memoria cuando el guardado esté autorizado y comprobado, sin ZIP.

El ZIP del relevo debe bastar para el trabajo definido, sin exigir descargar piezas dispersas evitables. Las reglas de conservación de versiones siguen aplicando al conjunto pertinente; no obligan a inventar versiones ni a incluir archivos ajenos al trabajo. Ubicar el único enlace principal en `DESCARGAS Y UBICACIÓN`, al final de la respuesta.

## Regla de salida — UBICACIÓN EXACTA, OBLIGATORIA

**Todos los enlaces de descarga, sin excepción, aparecen juntos en una sección única al final absoluto de la respuesta, DESPUÉS de `NOTA FINAL`, bloqueos y preguntas necesarias.** No colocar enlaces a artefactos al principio, a mitad de los hallazgos, dentro de tablas de estado, junto a cada prueba ni antes de `NOTA FINAL`. El bloque final se titula **`DESCARGAS Y UBICACIÓN`**. Bajo cada enlace agrupar nombre, versión, estatus, ubicación recomendada, qué conserva y si sustituye una versión anterior; el texto explicativo completo puede ir antes de NOTA FINAL, pero la instrucción de ubicación debe quedar también junto al enlace. Después del último enlace no añadir texto.

Si el usuario pide exclusivamente contenido literal o un formato que prohíbe postámbulos, respetar esa restricción de mayor prioridad; no insertar enlaces ficticios. En cada respuesta solo enlazar archivos existentes verificados por herramienta/contenedor. Nunca inferir `sandbox:/mnt/data/...` a partir del nombre de un adjunto. Los enlaces a PR o páginas (no descargas) pueden aparecer en el cuerpo si son necesarios, pero las descargas son exclusivamente el bloque final.

## Orden obligatorio del bloque final

1. **ZIP acumulativo principal**, si existe y es completo: una sola descarga suficiente por defecto, seguida inmediatamente de su destino sugerido y acción de instalación/reemplazo. Priorizarlo sobre piezas dispersas.
2. **ZIP de nuevo incremento/versión**, solo si es útil por separado y el usuario lo necesita; indicar que ya se incluye dentro del pack principal para evitar ambigüedad.
3. **Evidencias/manifest/guías externas al pack**, solo si no están incorporadas o se solicitan individualmente.
4. **Pack siguiente**, si la capacidad obliga a dividir la entrega; no presentar v2 como sustituto destructivo de v1.

No hay obligación de mostrar más de un enlace si el ZIP acumulativo ya contiene todo lo disponible. Si una entrega no tiene archivo descargable, omitir el bloque en lugar de inventar enlace.

## Versiones, conservación y límites

- Antes de empaquetar, inventariar artefactos disponibles y su versión comprobable, SHA/longitud, padre, dependencias y estado; distinguir código fuente, instalador incremental, pack y evidencia.
- Entregar **PACK ACUMULATIVO con todas las versiones realmente disponibles** del conjunto pertinente. No fabricar versiones anteriores a partir de resúmenes ni declarar incluidas versiones NO_RECUPERADO. Conservar cada versión con identidad y nombre propios; no sobrescribir archivos históricos.
- Identificador recomendado por proyecto: `BAM_VERSION_PACK_vN.zip` o equivalente del proyecto (para Alife: `ALIFE_PRIVATE_VERSION_PACK_vN.zip`). Conservar `VERSIONES.md`, `LEEME.md`, `INVENTARIO` o manifest y `SHA256SUMS.txt`. Mantener contratos, scripts y evidencias útiles. Registrar la versión base y la nueva; si la nueva es superior, explicar si se INSTALA SOBRE LA ANTERIOR, sustituye archivos concretos, se extrae en carpeta nueva, o es solo documentación.
- Cuando el paquete alcance el límite técnico de tamaño/cantidad de archivos, cerrar el pack actual y comenzar **PACK DE VERSIONES V2/V3...**, enlazando continuidad y faltantes. No reducir integridad, saltarse versiones recuperadas o borrar el pack anterior silenciosamente. No inferir que un pack de versiones de un proyecto contiene fuentes privadas de otro.
- **Lugar recomendado, no ruta supuesta:** sugerir una carpeta relativa bajo el proyecto, por ejemplo `<RAÍZ_PROYECTO>/entregas/<PRODUCTO>/PACK_vN/`, y describir rutas internas exactas del ZIP; si se sabe un directorio del usuario de forma comprobada, usarlo. Diferenciar carpeta de DESCARGA, EXTRAÍDO, INSTALACIÓN y EVIDENCIAS.
- Nunca publicar credenciales, material privado, recuerdos o cuerpos de conversación en repos públicos como paso de empaquetado. No convertir la entrega de artefacto en permiso de desplegar o modificar producción.
- La integridad `SHA256SUMS` demuestra igualdad de bytes respecto al inventario medido; no equivale a que el runtime funcione, que exista un servidor ni que se haya verificado Windows o producción.

## Validación y cierre

Comprobar el ZIP reabriéndolo, nombres/rutas y hashes; verificar que todas las versiones declaradas están realmente dentro; ejecutar tests pertinentes cuando se permitan y registrar PASS/FAIL/NOT_RUN. La actualización de plugin debe conservar todas las skills y bindings anteriores y comprobar versión y archivo tras publicar. Si falta una fuente, etiquetar `NO_RECUPERADO` antes de pedirla.

**Plantilla de orden** (sin enlaces inventados):

```
[Resultados / estados / límites]

NOTA FINAL
Estado, bloqueos y próxima acción. Preguntas imprescindibles, si las hay.

DESCARGAS Y UBICACIÓN
[PACK acumulativo vN](sandbox:/mnt/data/<ARCHIVO_EXISTENTE>.zip)
Destino sugerido: <RAÍZ_PROYECTO>/entregas/<PRODUCTO>/PACK_vN/
Versión: <N>; contiene <versiones verificadas>. Acción: <conservar pack anterior; extraer en carpeta nueva / parche concreto>.
```

La plantilla anterior es únicamente una pauta textual: verificar cada ruta y archivo antes de insertar un enlace. No imprimir marcadores ficticios en la respuesta final.

## Procedimientos según el encargo

Elige únicamente el procedimiento correspondiente al objeto y al resultado pedido.

- [Corrige la identidad y versión del instalador BAGO](../bago5-identidad-instalador/procedimiento.md).
- [Alinea fuentes, instalación y archivos de distribución](../bago5-sincronizacion-instalador/procedimiento.md).
