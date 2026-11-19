---
name: bago5-frontend
description: Cambia una interfaz real preservando navegación, estado, accesibilidad y contrato con la aplicación.
---

# Implementar y comprobar una interfaz

1. Recorre la pantalla actual desde su entrada normal. Identifica usuarios, tareas, componentes reutilizables, navegación, origen de datos y dimensiones acordadas.

2. Implementa el flujo principal y los estados de carga, vacío, error y recuperación. Conserva filtros y posición al volver cuando formen parte de la tarea. Usa nombres accesibles y orden de foco coherente.

3. Comprueba en la interfaz ejecutada la acción principal, un error recuperable y el recorrido con teclado. Revisa el texto y la distribución al ancho objetivo. Si hay un editor, comprueba la salida con cambios pendientes.

## Criterio de cierre

Entrega la ruta, candidata, estados recorridos y evidencia visual cuando aplique. Indica si se usó un servicio real o un doble. Si solo pasó la compilación, deja pendiente la interacción en navegador.

