# Evidencia del incremento 0.2.0

- Línea base: BAGO5 Gobernado 0.1.9 (56 archivos de plugin; release `pluginrel_6aefbd7423748191a4c4e289cae6d8ab`). Memoria Viva v1 = 0.1.8, sin modificar.
- Pieza de referencia: MYTHOS 1.0.4 / `codex-memory-handoff-mythos`; se adopta el procedimiento de identificación, selección y conexión verificable, no la conexión MYTHOS ni sus recuerdos.
- Candidata: BAGO5 Gobernado 0.2.0, skill `bago5-memorias-conectadas` y backend local SQLite/HTTP. Conservar plugin y namespace general.
- Esquemas: `schemas/connection.schema.json`, `schemas/invitation.schema.json`, `schemas/pack-manifest.schema.json`; vectores: `references/verification-vectors.json`. La biblioteca valida las entradas con reglas concretas sin dependencia externa de jsonschema.
- Tests: `python -m unittest discover -s skills/bago5-memorias-conectadas/tests -v`; registrar el log de esta ejecución y su entorno antes de declarar PASS.
- Alcance de las pruebas: procesos Python locales, SQLite y HTTP en loopback; NO cubren instalación nueva de plugin, delegación de chat a skill, Sites, cuentas externas, OAuth, navegador, despliegue o autenticación por identidad real en Internet.
- Positivos requeridos: varios alias persisten, roles por scope, invitación aceptada por destinatario autenticado, export/import con historial y flags, vista previa sin efectos, idempotencia.
- Negativos requeridos: token incorrecto, receptor incorrecto, revocación, invitación caducada, viewer escritura negada, alias duplicado, URL con contraseña/token, pack modificado, entrada ZIP extraña, snapshots inconsistentes, conflicto importación, edición con versión antigua.
- Si todo PASS en pruebas locales: capacidad `IMPLEMENTED/VERIFIED_LOCAL`, Site externo `BLOQUEADO_SITES` y plugin host `NOT_RUN`. No declarar GO para compartir memoria Site remota sin nuevos contratos y pruebas de autorización.
