---
name: bago5-ganchos-sesion
description: "Coordina inicio, memoria, continuidad, cierre y STOP mediante los ganchos disponibles o el procedimiento del agente."
---

# Ciclo de sesión

Identifica el proyecto, el objetivo, los permisos y la última evidencia al iniciar o recuperar una tarea. Aplica la selección del usuario antes de acceder a memoria o archivos. Cada efecto requiere un destino identificado y un permiso vigente. Con STOP, detén la operación afectada.

Para guardar un registro, comprueba la identidad y versión, escribe solo el cambio solicitado y vuelve a leerlo. Al cerrar, comunica lo ejecutado, lo comprobado y las operaciones pendientes. El cliente web coordina estos pasos durante la conversación. Un cliente local que ya tenga integraciones instaladas debe verificar su propia configuración antes de atribuirles eventos.

En Codex, aplica el [formato de respuesta de BAGO](../bago5/SKILL.md#respuestas-en-codex) al comunicar el resultado.
