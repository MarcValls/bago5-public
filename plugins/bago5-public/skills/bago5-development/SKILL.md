---
name: bago5-development
description: Implementa un cambio de software con preservación de contratos, datos existentes y comprobación de regresiones.
---

# Implementar un cambio verificable

1. Localiza el punto de entrada y reproduce el comportamiento de partida. Anota las variantes admitidas y la condición observable que debe cambiar.

2. Reutiliza las representaciones y servicios existentes. Aplica el cambio mínimo completo a través de los consumidores reales. Comprueba datos antiguos, concurrencia o reintentos cuando el flujo los admita.

3. Ejecuta la comprobación más próxima al defecto y un recorrido de regresión representativo. Si una operación falla a mitad, verifica que el estado permite recuperación. Examina el diff final y los archivos ajenos al encargo.

## Criterio de cierre

Entrega la candidata exacta, los cambios y resultados por prueba. Un ensayo con datos sintéticos conserva ese alcance. Declara NOT_RUN para comprobaciones que dependan de un entorno ausente.

