# Frontend Contracts — BAGO5 v0.1 (pack conservado)

**Tipo:** referencia normativa y maqueta offline, NO aplicación conectada.
**Origen:** `../../integrations/source-packs/BAGO5_FRONTEND_PACKS_v0.1.zip`.

BAGO Operating Layer sigue siendo la autoridad. Este módulo solo propone trabajo del frontend en BAGO5. Antes de cualquier modificación inspecciona el repositorio objetivo, identifica servicios owners, rama y SHA. Nunca dupliques registries ni permisos. Preserva BAGO5-CONFIG-001/002 y la separación Global/Proyecto/Agente/Chat; registrar fuente no concede acceso; proveedor/modelo habilitado no habilita herramientas ni permisos. La preview contiene simulaciones, no conexión real. Las acciones con coste explícito requieren confirmación. Prueba negativos, 7 screens y conservación de elementos previos según `PACK_06_QA_REGRESSION/README.md` dentro del ZIP.

**Orquestador:** `python scripts/suite_orchestrator.py plan --modules frontend ...` o `verify --modules frontend` desde raíz de skill. Verificar el pack no prueba UI real.

**GATE:** NOT_RUN para frontend host y E2E hasta prueba en repo y navegador con evidencia.

## Vista derivada auditada 1.3.1

`preview_auditada.html` es una derivación explícita de la maqueta del pack, no una sustitución silenciosa del ZIP fuente. `PREVIEW_PROVENANCE.json` conserva las huellas del HTML original y del derivado. Corrige la edición de proveedor (sin duplicar identidad), precarga campos y mejora etiquetas y navegación de teclado del diálogo. El exportador verifica ambas huellas antes de escribir la vista.

La QA de navegador corresponde únicamente a esta maqueta offline. No demuestra conexión a BAGO5, permisos reales, almacenamiento persistente ni disponibilidad de modelos.


Esta operación necesita el motor local indicado, instalado y autorizado por separado en el equipo del usuario.
