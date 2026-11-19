---
name: bago5-decision-ui-engineer
description: Construye una pantalla de decisiones que respeta el contrato de datos, los permisos y los estados desconocidos.
---

# Implementar una interfaz de decisiones

1. Lee el contrato aceptado y selecciona una muestra de cada estado. Identifica la procedencia de conclusión, fuente, confianza, fecha y acciones disponibles.

2. Implementa los componentes con la convención existente. Representa explícitamente información ausente, caducada, contradictoria y en carga. Conserva identificadores en las acciones para evitar aplicar una decisión a otro registro.

3. Vincula los cambios a la API autorizada. Mantén distinguibles el envío, la confirmación del servidor y el fallo. Protege el reintento de un doble envío y restituye foco tras cerrar el diálogo.

## Criterio de cierre

Comprueba con teclado un caso permitido, otro sin permiso y una respuesta fallida. Entrega cambios, casos recorridos y desviaciones del contrato. Si el diseño requiere un dato nuevo, remite el cambio al propietario del contrato.

