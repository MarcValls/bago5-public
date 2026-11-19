---
name: bago5-governance-action-engineer
description: "Diseñar y probar los estados de una acción propuesta por un agente, desde la autorización hasta el recibo."
---

# Controlar acciones con efectos

Modela por separado capacidad, elegibilidad, aprobación, disponibilidad del ejecutor, ejecución y recibo. Describe acción, destino, parámetros, riesgo, responsable y vigencia. Asocia la decisión al contenido concreto de la acción para detectar cambios posteriores.

Antes del efecto, comprueba el estado vigente de permisos, revocaciones y autorizaciones. Registra intento, motivo de rechazo o fallo, y un identificador que permita reconciliar una respuesta incierta. Antes de reintentar una operación con efectos, consulta el recibo o el estado del destino.

Prueba propuesta sin autorización, aprobación vencida, rechazo explícito, fallo del ejecutor, recibo ausente y recibo de otra candidata. Entrega el contrato de estados y las observaciones de cada transición. Una ejecución sin confirmación conserva su estado incierto.
