---
name: bago5-reparador
description: "Diagnosticar fallos entre código, paquete instalado y entorno de ejecución."
---

# Diagnosticar fallos entre código, paquete instalado y entorno de ejecución

Identifica la entrada que usa realmente el usuario. Registra las versiones y las rutas seleccionadas para fuente, artefacto y runtime. Sigue la llamada hasta el componente que presenta el fallo y distingue instalación obsoleta, configuración, datos e implementación.

Para comparar archivos relativos explícitos de dos raíces autorizadas, ejecuta `python scripts/compare_copies.py FUENTE DESTINO ARCHIVO [ARCHIVO ...]` desde esta habilidad. El recibo distingue igualdad de bytes, diferencia y ausencia. Reproduce el problema con el destino observado, aplica la corrección en la fuente responsable y repite el recorrido. Guarda la evidencia antes y después.
