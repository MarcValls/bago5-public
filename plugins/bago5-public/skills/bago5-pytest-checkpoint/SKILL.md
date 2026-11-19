---
name: bago5-pytest-checkpoint
description: "Ejecutar o reanudar pruebas Python solicitadas con recibos vinculados a la candidata y al entorno."
---

# Guardar un punto de comprobación de pytest

Resuelve la candidata por revisión o SHA-256, el directorio de ejecución, intérprete, configuración, selección de pruebas y comando del proyecto. Comprueba si los datos o servicios necesarios están disponibles. Ejecuta el comando autorizado y conserva su código de salida, selección, resultado y evidencia.

Cuando se haya autorizado persistir el estado, crea un recibo que cumpla el [esquema del checkpoint](references/checkpoint.schema.json) y reléelo tras escribirlo. Distingue los casos ejecutados de los omitidos, fallidos o pendientes. Conserva fuera de los registros parámetros sensibles.

Para reanudar, vuelve a medir candidata, ámbito y entorno y comprueba que el recibo y la evidencia sean recuperables. Un cambio de configuración o de datos relevante exige nuevas pruebas. Un resultado previo describe una ejecución anterior. Entrega el comando, el alcance probado y los impedimentos para repetirlo.
