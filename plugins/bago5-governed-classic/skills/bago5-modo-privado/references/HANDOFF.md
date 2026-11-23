# GPT -> host local · Continuidad ejecutable BAGO-PRIVATE-001

Objetivo: conectar la cesión privada a un host real sin permitir al modelo observar
secreto/cuenta/vault. Fuente: plugin BAGO5 0.4.22, carpeta skills/bago5-modo-privado.
Este trabajo añade código y protocolo; no autoriza instalar gestores, crear vaults,
modificar ACLs, abrir secretos, exponer nuevas herramientas o lanzar otros agentes.
Revalidar permisos y host antes de actuar. STOP conserva prioridad. No trasladar
las autorizaciones de GPT a otra sesión. Mantener el resto del plugin y M0 intactos.

1. Localizar el host/checkout REAL, versión, rama, estado dirty y AGENTS.md; no adoptar
   el runtime histórico BAGO-4.11.10 empaquetado como producción. Identificar dispatcher,
   planificador, streams, agentes y sesiones de observación realmente activos.
2. Ejecutar primero la batería sintética del módulo, guardar resultados y candidata.
   `python -B -m unittest discover -s skills/bago5-modo-privado/tests -v`.
3. Implementar HostBoundary con la arquitectura existente. Determinar cobertura total,
   parada, buffers, tokens y tickets huérfanos. Toda ruta controlada debe quedar bajo
   el gate o bajo el mecanismo equivalente ya existente. Falta de cobertura => BLOCKED.
4. Instanciar Coordinator/Gate/WindowsKeePassXC en el backend confiable, no como tools
   invocables por el LLM. Conectar `private_ui.show(coordinator)` a una interacción
   local explícita. Bootstrap y finish pertenecen a la UI humana/host, no MCP.
5. Verificar instalación y pins del ejecutable por procedencia legítima, ACLs del
   estado y configuración, firma, entorno y ausencia de argumentos secretos. No
   generar un pin a partir de un binario no acreditado y llamarlo confiable.
6. Repetir la aceptación con datos ficticios en Windows: herramientas reales denegadas,
   captura activa cancelada, multisesión, buffers, fallo/reinicio, cancelación y retorno
   explícito, no guardado supuesto. Buscar secretos de ensayo en salidas, logs, argv
   y entorno del perímetro controlado. No inspeccionar un vault real como prueba.
7. Conservar evidencias por versión y cobertura. No declarar PASS global ni privacidad
   operativa por los tests del core. Si faltan canales, detener la capacidad sensible.

Implementado y comprobado: core cooperativo + UI con fixtures. Pendiente: adaptador
real, Windows/Authenticode/KeePassXC efectivo, recuperación administrada de huérfanos,
prueba end-to-end y aceptación del usuario. No hay agente trabajando en segundo plano.
