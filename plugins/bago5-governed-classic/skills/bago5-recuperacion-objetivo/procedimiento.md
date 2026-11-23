# BAGO5-CCR-001 · continuidad del objetivo tras caducidad de una acción

**Regla obligatoria:** caducidad de acción != caducidad del objetivo != caducidad de permiso. El bloqueo de la acción caducada es terminal solo para esa instancia. La misión mantiene sus criterios, obligaciones, permisos actuales y restricciones. No convertir una acción EXPIRED/OBSOLETE en RESOLVED. No borrar ni sobrescribir el registro histórico.

Cuando una acción expire o resulte obsoleta:

1. Recuperar el binding de proyecto, misión, goal_id, goal_revision, candidata, alcance y sesión, el objetivo literal y criterios originales. Comprobar STOP y revocaciones antes de cualquier lectura o efecto.
2. Determinar qué caducó: evidencia/observación, autorización, límite explícito de la orden o simple viabilidad/pertinencia de esa instancia. No confundir pérdida de prueba con pérdida de objetivo.
3. Si caducó la observación, reevaluar las condiciones con fuentes actuales. Si caducó permiso, no ejecutar hasta obtener una autorización vigente. Si caducó orden, dejar su registro EXPIRED/OBSOLETE y valorar una nueva acción independiente solo si sigue dentro del objetivo y alcance.
4. No inventar una autorización: una nueva acción puede usar un permiso **ya vigente y aplicable exactamente a su efecto y destino**, comprobado mediante el mecanismo real del host. No solicitar nueva aprobación rutinaria si ya está cubierto; solicitarla si amplía alcance, viola tiempo límite, renueva una autorización caducada/revocada, o requiere una decisión reservada al usuario. La duración de una autorización no se infiere del goal_id.
5. Para sustitución, usar `skills/bago5/scripts/objective_continuation.py` sobre un registro `behavior-recovery.v1` terminal y un recibo `turn-decision.v1` actual. Solo evalúa, no ejecuta ni persiste. La salida REASSESS no reactiva la orden antigua y no sustituye el control de autorización real. Si falta prueba actual, BLOCKED; continuar tareas independientes autorizadas.
6. Conservar en handoff y estado de misión los IDs, fecha, causa, código de la orden retirada, restricciones y prueba de la nueva selección. Nuevo objetivo no se crea implícitamente, no repetir la orden expirado y no reanudar STOP.

Si el mecanismo de sesión en uso conserva una corrección terminal, mantenerla archivada y registrar una nueva instancia separada de acción en el recibo, nunca reemplazar la historia de la anterior. Las transiciones siguen usando el controlador y su ExecutionGateway real. Si el registro terminal procede de una PROHIBITION o contiene efecto incierto, el adaptador devuelve BLOCKED hasta una resolución independiente conforme a la autoridad real y reconciliación verificable. No crear otro planificador, permisos, scheduler ni agente residente.

## Pruebas mínimas

PASS positivo: objetivo vigente y nueva acción autorizada → REASSESS/CONTINUE evaluable. Negativos: orden antigua presente, permiso revocado o desconocido, STOP, modificación del objetivo o criterios, ausencia de nueva acción, superación de límite explícito, efecto distinto del autorizado y cierre ya satisfecho. La prueba del evaluador no demuestra instalación en Windows ni ejecución del host.
