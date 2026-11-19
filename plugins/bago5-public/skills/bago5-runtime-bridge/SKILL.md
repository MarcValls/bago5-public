---
name: bago5-runtime-bridge
description: "Comprobar si un runtime disponible puede ejecutar una operación concreta."
---

# Comprobar si un runtime disponible puede ejecutar una operación concreta

Identifica el ejecutable del destino mediante su ruta autorizada, versión, ayuda y prueba de solo lectura. Comprueba el contrato de entrada, compatibilidad del host, dependencias y alcance de acceso. Distingue un runtime instalado, un paquete disponible y un servicio alcanzable.

Vincula cada operación al proyecto, candidata y permisos vigentes. Los comandos, procesos y conectores solo existen cuando se pueden comprobar en el host. Si falta el ejecutor, deja la operación `NOT_RUN`, documenta su entrada y salida esperadas y completa el análisis que pueda hacerse localmente.
