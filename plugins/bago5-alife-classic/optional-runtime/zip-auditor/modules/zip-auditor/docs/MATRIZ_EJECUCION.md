# Matriz de ejecución y trazabilidad · BAGO5os + ZIP Auditor

| Entrada | Enrutamiento | Efecto permitido | Verificación |
| --- | --- | --- | --- |
| `BAGO5os_...SETUP.exe` menú | Go installer, payload SHA+manifest+stage | Instalación autorizada por ruta; backups en sustituciones | Go SHA-256 de todas las entradas; en Windows `BAGO5os.exe --verify` |
| `BAGO5os.exe` panel | Go launcher → suite_orchestrator.py | Menú de Suite y especialista | `BAGO5os.exe --verify` |
| `BAGO5os.exe identity` | suite_orchestrator → suite_identity | Sólo lectura de la Suite instalada | SHA-256 de cada archivo y la identidad derivada |
| `BAGO5os.exe zip-auditor --verificar` | suite_orchestrator → suite_zip_auditor → terminal → VERIFICAR_PACK | Sólo lectura del motor | Comprobación 8 entradas del motor, más identidad Suite |
| `BAGO5os.exe zip-auditor --analizar RUTA --no-open` | terminal → un_clic → zip_auditor.py → zip_analysis/zip_reporting → verify_results.py → fusion_analysis.py → content_grouping.py | Informe, grupos, posibles fusiones, salida EXTERNA; sin tocar ZIP de origen | verificacion.json, SHA256SUMS.json, hashes de fuente, suite identity |
| Menú `ZIP Auditor` → `Revisar y aplicar última agrupación` | terminal.validate_current_plan → grouped_output.apply_grouping | Copia de los ZIP completos **solo** tras `Sí` explícito; no fusiona código | Plan sellado, revalidación origen, manifiesto de procedencia |
| `--aceptar-agrupacion` con `--analizar` | terminal.apply_or_decline → grouped_output | Copias opt-in; jamás implícitas | SHA-256 antes/después, rollback de copias parciales |

**Conexión funcional:** 7 componentes principales Python (`terminal`, `un_clic`, `zip_auditor`, `zip_analysis`, `verify_results`, `fusion_analysis`, `content_grouping`) y auxiliares (`zip_reporting`, `grouped_output`, `VERIFICAR_PACK`) se referencian desde las rutas precedentes. No se ejecutan los ZIP de entrada.

**STOP:** ninguna ruta de ejecución instala servicios, ganchos o agentes; el puente no concede permisos de host. El acceso al sistema de archivos y la aceptación de copias siguen siendo operaciones explícitas y separadas. La Suite conserva sus contratos de STOP originales.

**Limitaciones:** FIX02 descarta candidaturas basadas únicamente en nombres genéricos de raíz de diferente contenido, pero otras colisiones y señales requieren revisión. La equivalencia funcional de programas no es verificada; la decisión de fusión sigue siendo humana.


## Derivada FIX02 — cierre de colisiones genéricas

- No se detecta parentesco ni compatibilidad por `README.md` y `package.json` con hashes diferentes.
- Las colisiones de código y los inventarios parciales siguen visibles.
- No se copian ni fusionan ZIP en el análisis.
- Windows real: NOT_RUN.
