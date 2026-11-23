# Encargo acotado para Codex — protección de evidencias W12

**Objetivo:** incorporar el ejecutable Python `bago_evidence_guard.py` como herramienta determinista de **preaceptación de informes**, sin alterar BAGO5os 1.4.7 RC4, TaskStore ni los expedientes r1–r4.

**Inicio:** inspeccionar el esquema real de `W12-independent-review-20261103-r4.json` y listar sus 15 campos que afirman SHA-256 de archivos. El archivo r4 no está incluido en este pack; no suponer que coincide con `examples/W12_TEMPLATE_SINTETICO.json`.

**Contrato:** escribir un archivo independiente `vinculos_W12.json` con `expected_count:15` y exactamente 15 objetos `{pointer,path}`, relativos a una raíz autorizada que contenga sus 15 archivos. Cada `pointer` debe señalar el digest real del documento; si hay claves dinámicas, escapar `~` como `~0` y `/` como `~1` según JSON Pointer.

**Pruebas antes de aceptar:** ejecutar `check-text` sobre r4 JSON y MD, y `verify-json --expected-count 15` sobre r4; conservar stdout/exit code con hora, hash del script y hash de la configuración, sin reescribir el contenido de r4. Provocar en copia sintética digests de 65 caracteres y controles prohibidos y observar FAIL.

**Generación futura:** si se necesita otra revisión con la estructura W12, construir una plantilla con los quince placeholders `__SHA256__` y ejecutar `seal-json`. Recalcular de nuevo con `verify-json` sobre el archivo final. En caso de cambios de fuentes, no reutilizar hashes de una candidata anterior.

**Conservación y seguridad:** los informes previos son solo lectura, la salida utiliza nombre nuevo; no efectuar cierres, commits, instalaciones, limpiezas ni reanudaciones en nombre de esta herramienta. Respetar STOP y permisos. Nunca inferir que un hash válido equivale a un proceso funcional, autorización o revisión independiente.

**Criterios de aceptación:** 24 tests PASS en Windows + demo sintética PASS; r4 `check-text` PASS; r4 `verify-json` 15/15 PASS sobre los mismos bytes declarados; JSON futuro sellado y verificado, sin modificar r1–r4; control de ausencia de efectos secundarios; README de uso. Si una condición no se ejecutó: `NOT_RUN`.
