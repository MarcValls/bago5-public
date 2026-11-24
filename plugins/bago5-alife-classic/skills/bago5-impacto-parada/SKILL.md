---
name: bago5-impacto-parada
description: "Delimita acciones, tiempos y dependencias afectados por STOP o una desviación, distinguiendo daño y riesgo."
---

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# #BAGO5-stop-impact · Delimitación de desviaciones

Para una parada, distinguir `t_d` (comienzo desviación), `t_s` (STOP solicitado), `t_p` (parada efectiva).

Tiempo afectado: `(t_s - t_d) + (t_p - t_s)`. Si `t_d` es incierto, acotar entre último punto comprobado válido y primer punto comprobado desviado.

Con grafo de dependencias, sea `D` el conjunto identificado como desviado; `R = D ∪ Descendientes(D)` es zona a REVISAR, no necesariamente dañada. Si se pondera `P = sum(w_i de R)/sum(w_i de A)`, indicar qué peso mide (tiempo, coste, impacto), sin mezclar magnitudes.

Fuentes exigidas: objetivos y permisos vigentes, baseline, acciones del ejecutor y sus fechas, versiones y enlaces de dependencias, eventos de STOP. Un mensaje posterior es declaración, no log independiente. Si faltan artefactos, identificar `NO_RECUPERADO`, no estimar precisión falsa.

STOP en este chat interrumpe nuevas acciones propias. No atribuir control de procesos externos. No reanudar sin petición explícita.

Para una corrección sin STOP global, aplicar [BAGO5-CCR-001](../bago5/references/behavior-recovery.md): delimitar la conducta afectada y conservar las condiciones para recuperar la conducta válida. La zona a revisar no equivale a una cancelación del objetivo ni a una prohibición permanente. Conservar el último estado y las evidencias ya existentes; un STOP conocido no autoriza nuevas comprobaciones, registros ni escrituras de despedida. Tras una reanudación explícita, revalidar necesidad, identidad, candidata, restricciones y permisos actuales. La recuperación de una dependencia técnica no levanta STOP ni revocaciones, y no obliga a repetir acciones que ya sean innecesarias.
