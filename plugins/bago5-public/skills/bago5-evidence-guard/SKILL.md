---
name: bago5-evidence-guard
description: Genera o verifica un manifiesto de archivos y contrasta las huellas declaradas en un informe.
---

# Comprobar la integridad de evidencias

1. Define raíz autorizada, inventario, finalidad de cada archivo y bytes exactos que se van a comprobar. Rechaza rutas fuera de la raíz y datos de texto ambiguos.

2. Para generar un manifiesto crea una salida nueva y calcula SHA-256 del contenido original. Para un informe JSON relaciona cada afirmación con su puntero y el archivo que la sustenta.

3. El verificador portable se ejecuta con `python scripts/bago_evidence_guard.py --help`. Consulta `create-manifest --help` o `verify-json --help` para sus entradas. `check-text` comprueba controles y claves duplicadas. `verify-manifest` recalcula las huellas desde las fuentes.

## Criterio de cierre

Repite la verificación en la entrega final. Indica cobertura parcial si alguna afirmación quedó sin vincular. Un digest coincidente acredita identidad de bytes y necesita evidencia adicional para demostrar autoría o ejecución.

