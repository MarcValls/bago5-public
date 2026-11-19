---
name: bago5-rc4-goals
description: "Coordinar objetivos con un controlador local cuando el host lo ofrece."
---

# Coordinar objetivos con un controlador local cuando el host lo ofrece

Comprueba la identidad del controlador de tareas, su versión, el directorio de trabajo, la raíz de estado y el objetivo seleccionado. Lee su diagnóstico y el estado pendiente antes de preparar un despacho. Un resumen de recuperación sirve para inspeccionar el estado.

Antes de ejecutar, coteja el objetivo, el trabajo, el alcance y los permisos efectivos. Usa una sola fuente para las asignaciones. Separa la orden de parada del usuario, el bloqueo persistente del controlador y la cancelación observada de un proceso. Reanuda solo el objetivo indicado mediante el mecanismo autorizado. Sin controlador compatible, prepara un relevo y marca el despacho `NOT_RUN`.
