---
name: bago5-pruebas-python
description: Ejecutar y recuperar una campaña de pruebas Python.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](../bago5/references/controles-especialistas.md#efecto).

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# Ejecución y checkpoint de pruebas

No ejecutes pruebas por instalar este plugin ni solo porque haya código. Activa esta ruta cuando el usuario solicite una ejecución o reanudación. Lee instrucciones del proyecto y selecciona el comando de prueba existente; no lo reemplaces por otro.

Registra, cuando el usuario autorice la persistencia, ID de tarea, candidata (commit o SHA-256 de los archivos pertinentes), comando exacto, entorno visible, fecha, código de salida, ubicación/log y estado. Usa references/checkpoint.schema.json para un recibo manual. Léelo de nuevo tras escribir. Nunca registres una prueba que no se ejecutó.

Para reanudar, vuelve a calcular identidad de candidata y verifica comando, entorno y log previos. Si la candidata o el alcance cambiaron, no reutilices el checkpoint. Un resultado cacheado es evidencia de una ejecución anterior, no un permiso, proceso activo o release verificada. El companion pytest-checkpoint de la Suite solo se usa si el host lo expone y su identidad se verifica; indica la ruta de la instalación externa.

Para la implementacion incluida, aplicar [puente de runtime](../bago5-acceso-motor-local/SKILL.md) y conservar candidata y controlador de mision.

## Procedimientos según el encargo

Elige únicamente el procedimiento correspondiente al objeto y al resultado pedido.
