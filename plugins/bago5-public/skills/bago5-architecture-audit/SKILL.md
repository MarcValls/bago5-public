---
name: bago5-architecture-audit
description: Rastrea dependencias, límites de módulos y contratos a partir de puntos de entrada reales.
---

# Auditar la arquitectura

1. Fija revisión, estado local y alcance. Identifica quién es dueño de los datos y qué componentes pueden modificarlos.

2. Para cada flujo crítico reconstruye la cadena desde la interfaz hasta la persistencia o servicio externo. Sigue registros dinámicos, importaciones, inyección y errores. Dibuja las direcciones de dependencia y señala los cruces de responsabilidad.

3. Contrasta el diseño documentado con los consumidores reales y las pruebas. Busca una segunda ruta legítima antes de atribuir duplicación o marcar código como inaccesible.

## Criterio de cierre

Entrega un mapa de componentes y hallazgos con ubicación, recorrido, impacto y grado de confirmación. Mantén la auditoría de lectura dentro del corpus y registra como desconocidos los componentes inaccesibles.

