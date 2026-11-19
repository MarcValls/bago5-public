---
name: bago5-stop-impact
description: "Determinar qué operaciones quedan afectadas por una parada o revocación."
---

# Determinar qué operaciones quedan afectadas por una parada o revocación

Registra el origen y el alcance de la orden. Identifica trabajos pendientes, operaciones ya enviadas, procesos, colas y datos potencialmente escritos. Detén nuevas acciones afectadas y usa cancelación solo si está disponible y autorizada.

Comprueba por separado el estado del controlador, el proceso y el destino. Deja como incierto cualquier efecto sin recibo. Permite que continúe el trabajo independiente autorizado. Una reanudación explícita exige reconciliar los efectos previos y cotejar de nuevo candidata, permisos y alcance antes de ejecutar.
