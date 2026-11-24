---
name: bago5-repositorios-github
description: Administrar el repositorio remoto y sus permisos autorizados.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](../bago5/references/controles-especialistas.md#efecto).

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# BAGO5-GITHUB-CREATE

Aplicar bago5 y el contrato GPT Classic.

Resolver propietario, nombre, visibilidad, descripcion e inicializacion desde la solicitud. Descubrir una herramienta real de creacion GitHub y revisar sus parametros; no inventar create_repository ni suponer credenciales disponibles. Si falta, preparar los parametros y marcar ejecucion NOT_RUN.

Crear solo dentro del alcance autorizado. No leer ni imprimir tokens. Tras la creacion, leer el repositorio por su identidad y comprobar propietario, nombre, visibilidad, ID y URL. Un POST exitoso acredita EXECUTED; VERIFIED exige lectura coincidente. Ante resultado incierto buscar el repositorio antes de reintentar, sin crear uno alternativo. No borrar, transferir, archivar ni cambiar visibilidad por esta ruta. Registrar fuente de verificacion y limites.

Esta ruta usa una herramienta GitHub realmente disponible en el host. No incluye servidor MCP propio ni configura credenciales. Si no hay una herramienta capaz de crear y releer el repositorio, la operacion queda NOT_RUN.
