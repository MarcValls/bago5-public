[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# Auditoría de archivos comprimidos

Identifica archivo, propósito y alcance. Obtén primero inventario de entradas sin extraer; registra nombre, tamaño comprimido/descomprimido, hashes cuando proceda, manifiestos y archivos duplicados o rutas sospechosas. Comprueba raíz del paquete, estructura esperada y referencias a archivos ausentes. En Windows y Codex usa herramientas disponibles; Python zipfile/tarfile u otro lector debe limitarse al archivo identificado.

No ejecutes, importes ni abras binarios del archivo. No extraigas sobre el original ni sobrescribas una carpeta de usuario. Si una inspección interna requiere extracción, usa una carpeta nueva y aislada, verifica el destino y pide autorización cuando la extracción sea un efecto material.

Distingue estructura válida, integridad del archivo, identidad del paquete y funcionalidad instalada. La lista de entradas o un CRC correcto no demuestra que el plugin cargue. La base 0.2.4 usaba una adaptacion conversacional. La candidata unificada recupera ademas el motor FIX02 como se documenta mas abajo; el ZIP de origen y sus hashes se conservan en la evidencia de derivacion.

Para contradicciones dentro del contenido autorizado a leer, continuar con ../bago5-auditoria-semantica/SKILL.md. La referencia ahora inspeccionada ZIP_AUDITOR_v0.2.2_UN_CLIC(3).zip aporta el modelo de identidad por ocurrencia, comparación exacta/normalizada y evidencia de relaciones. Se adapta ese procedimiento; el motor ZIP, su lanzador y sus informes históricos no están incorporados como ejecutables. Separar integridad del contenedor de coherencia semántica del contenido.


## Motor opcional recuperado en la candidata unificada

Esta candidata incorpora ZIP Auditor 0.3.0 con adaptacion FIX02 bajo optional-runtime/zip-auditor. Las referencias anteriores a motor ausente describen la base 0.2.4, no esta candidata. El entrypoint es `python -B <plugin-root>/optional-runtime/zip-auditor/scripts/suite_zip_auditor.py --verificar`; para analisis usar `--analizar <carpeta-autorizada> --no-open`. No usar el subcomando zip-auditor de la Suite 1.4.8: ese router no lo incluye.

Definir BAGO_ZIPA_REPORTS_DIR fuera del paquete y de los ZIP originales. La agrupacion mediante copias requiere autorizacion especifica; el analisis por si solo no la concede. Los resultados de familias/fusiones son heuristicas y requieren revision. GPT Classic necesita acceso real al interprete y a los archivos mediante una herramienta de ejecucion; si falta, usar inspeccion de adjuntos y declarar motor NOT_RUN. El motor no ejecuta el contenido de ZIP inspeccionados.
