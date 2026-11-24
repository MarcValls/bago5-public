# Contrato de contexto M:\ y fronteras entre proyectos

Estado: **PROPUESTO**, basado en el mensaje del usuario de 2026-11-14. Es una proyección de trabajo; no equivale a haber leído ni validado `M:\AGENTS.md` o `M:\ARBOL_Y_RESPONSABILIDADES.md`.

| Ruta | Propósito / restricción |
|---|---|
| `M:\00_ENTRADA_DIARIA` | Bandeja de llegada; extracción comprimidos manual; catalogar no implica mover. |
| `M:\01_PROYECTOS\<NOMBRE>` | Código y fuente canónica de cada proyecto *si se confirma en sus reglas*. Repositorios individuales. |
| `M:\02_IA_Y_MODELOS` | Modelos, agentes, skills, MCP y evaluaciones; no trasladar automáticamente el plugin a una ruta global. |
| `M:\03_CONOCIMIENTO` | Investigación y referencias; no convertir en código o canon por clasificación. |
| `M:\04_DESARROLLO` | Herramientas, entornos, temporal; `ENTORNOS_SSD.cmd` ≠ `TEMPORAL_SSD.cmd`. |
| `M:\05_DATOS` | Importación/exportación de datos; no confundir con recuerdos canónicos. |
| `M:\06_EVIDENCIAS` | Pruebas, auditorías y recibos; destino condicionado a permisos. |
| `M:\07_ARTEFACTOS` | Releases, paquetes y sus versiones; crear únicamente con autorización. |
| `M:\08_BACKUPS` | Copias auxiliares locales; protección insuficiente frente a pérdida de M:. |
| `M:\09_CONTINUIDAD` | Sesiones, estados, handoffs; recuperar contexto ≠ reanudar tareas. |
| `M:\10_CATALOGADOS` | Material clasificado, expresamente no canónico. |
| `M:\99_SISTEMA` | Configuración, catálogo, automatización, informes; no es Git de un proyecto. |

## Invariantes

- No existe Git único en la raíz `M:\`.
- Separación de los proyectos (ejemplos: `ALIFEMEMORIES`, `MEMORIA_VIVA`, `BAGO5`, `MYTHOS`); una copia no promueve canon.
- La jerarquía de instrucciones aplicables se verifica en **cada proyecto** y en la sesión. Nada en una skill concede permisos de lectura/escritura.
- Los hooks «configurados» en Codex/Copilot no están probados como ejecutados en cada host.
- Preservación: no eliminar ni cambiar skills/herramientas anteriores para adaptar los manifests. Registrarlo como regresión si se detecta pérdida.
- Separación de estados: `PROPUESTO`, `IMPLEMENTADO`, `VERIFICADO`, `VALIDADO`, `NOT_RUN`, `FAIL`, `BLOQUEADO`.

## Tabla de decisiones por sesión

`proyecto` · `ruta_confirmada` · `canon` · `host` · `version_host` · `instrucciones_revisadas` · `memoria_autorizada` · `permisos` · `objetivo` · `plan_literal/versión` · `trabajo/ID` · `evidencias` · `estado` · `siguiente_acción`. No completar campos con suposiciones.
