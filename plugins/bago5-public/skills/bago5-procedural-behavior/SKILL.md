---
name: bago5-procedural-behavior
description: "Examinar procedimientos, efectos, transiciones, parada y evidencia mediante recorridos reproducibles."
---

# Auditar un procedimiento

Reconstruye el recorrido desde una entrada real hasta cada efecto: quién puede actuar, qué condiciones exige y qué estado queda registrado. Compara el procedimiento escrito con el comportamiento observado en una candidata identificada.

Ensaya el recorrido normal, entrada inválida, interrupción entre pasos y reintento. Comprueba que una autorización vencida o revocada detenga los efectos pendientes y que una orden de parada tenga un punto observable de aplicación. Verifica si dos participantes concurrentes pueden reclamar la misma tarea.

Entrega por hallazgo estado inicial, evento, resultado esperado, observación, evidencia y alcance. Si el procedimiento permite una transición inválida, propón el control mínimo y un caso de regresión. Distingue la inspección estática de lo ejecutado.
