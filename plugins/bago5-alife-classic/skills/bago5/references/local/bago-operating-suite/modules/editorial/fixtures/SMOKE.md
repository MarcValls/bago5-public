---
title: "BAGO — Prueba de integración editorial"
subtitle: "Documento sintético; no es el manual de producción"
author: "BAGO Operating Suite"
collection: "INTEGRACIÓN EDITORIAL"
volume: 1
edition: "1.4.0 · prueba local"
---

# Alcance de la prueba

Esta fuente sintética comprueba el recorrido de generación y conserva el texto original.
El resultado automático no constituye una revisión visual ni verifica BAGO5.

## Estados independientes

| Operación | Evidencia | Estado esperado |
| --- | --- | --- |
| Generación | HTML y PDF | Borrador |
| Controles automáticos | Informes y huellas | Comprobado |
| Revisión visual | Inspección explícita | Pendiente |
| Cierre | Recibo vigente | Bloqueado hasta revisión |

## Comprobación de código

```python
def identidad(contenido: bytes) -> str:
    import hashlib
    return hashlib.sha256(contenido).hexdigest()
```

## Conservación

Ningún fichero de la fuente debe modificarse. Cada salida ocupa un directorio nuevo.


Esta operación necesita el motor local indicado, instalado y autorizado por separado en el equipo del usuario.
