---
name: bago5-session-hooks
description: "Aplicar manualmente los controles de inicio, memoria, relevo y cierre."
---

# Aplicar manualmente los controles de inicio, memoria, relevo y cierre

Al inicio identifica host, misión, sesión, proyecto, candidata, alcance y parada. Conserva el almacén elegido por el usuario y verifica propietario, conector y permisos antes de leer o guardar. Repite los controles pertinentes cuando cambie un destino o se revoque el acceso.

Para escribir, relee la versión, preserva los campos ajenos al cambio y registra el intento con un identificador estable. Antes de volver a enviar un guardado incierto, reconcilia el resultado por una lectura autorizada. Al compactar o cerrar, conserva criterios, cambios y pruebas pendientes. Una parada explícita bloquea nuevos efectos. La [guarda de memoria](scripts/memory_guard.py) permite ensayar el contrato local con [datos sintéticos](tests/test_memory_guard.py); no activa hooks ni se conecta a un servicio.
