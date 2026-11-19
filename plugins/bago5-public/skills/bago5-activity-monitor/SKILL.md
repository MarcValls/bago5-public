---
name: bago5-activity-monitor
description: Consulta la actividad registrada y comprueba qué procesos siguen vivos durante una misión.
---

# Monitorizar tareas y procesos

1. Fija misión, directorio y hora de observación. Usa una fuente de estado que ya exista con acceso de lectura. Si el controlador guarda SQLite, necesita una instantánea consistente.

2. Obtén dos vistas. En la primera incluye tareas asignadas, bloqueos, última ejecución y fecha del registro. En la segunda consulta solo los identificadores de proceso vinculados a la misión y registra la hora de observación. Indica cuando el sistema operativo restringe esa consulta.

3. Desde esta habilidad puedes obtener una muestra con `python scripts/activity_monitor.py --root <directorio> --controller team --format json`. Para el controlador SQLite elige `--controller suite`. Con `--pid <número>` puedes contrastar un proceso concreto. Ajusta `--limit` para acotar la salida.

## Criterio de cierre

Entrega ambas vistas con fuente y hora, incluso si una está vacía. Un registro ACTIVE puede sobrevivir a su proceso. Si solo dispones de una captura anterior, identifica su fecha y deja la observación actual pendiente.

