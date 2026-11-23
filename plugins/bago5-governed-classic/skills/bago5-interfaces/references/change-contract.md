# Contrato de cambios frontend

Resolver proyecto, HEAD, worktree, cambios previos y canon UI vigente. Rutas historicas de BAGO (backend/docs/ui-canonical-contract.md, ui-system-visual-grammar.md, state-taxonomy.md y .gabo/copilot) solo son fuentes si existen y son autoridad en el proyecto seleccionado; no se transfieren a otro proyecto.

Seleccionar TRACE, AUDIT, PLAN/IMPLEMENT, REFACTOR, ADD_SURFACE, VERIFY o REFRESH_SURFACE_MAP segun la solicitud. Clasificar efectos FIX, REFACTOR, ADD_SURFACE, VISUAL_CHANGE, STATE_CHANGE, API_CONTRACT_CHANGE, PERFORMANCE o ACCESSIBILITY.

Trazar interaccion -> componente -> propietario de estado -> cliente/API -> backend -> respuesta/error -> reconciliacion/render -> pruebas. Una vista no demuestra una capacidad. El backend conserva autoridad de sesiones, proveedor/modelo efectivo, permisos, trabajos, seguridad y evidencias. El store compartido conserva presentacion compartida; el estado transitorio local permanece local. No persistir credenciales ni autoridad en UI.

Antes de editar definir alcance, invariantes, propietario, fallback/carga/error y gates. Preservar una navegacion, transporte y estado canonicos; no introducir rutas paralelas para arreglos locales. Probar aliases y migraciones persistidas. Revisar diff por estado duplicado, fetch ad hoc, credenciales persistidas, valores visuales dispersos y ausencia de estados bloqueado/error.

| Efecto | Evidencia aplicable del proyecto |
|---|---|
| Logica TypeScript | prueba focalizada y typecheck |
| Navegacion/estado | typecheck e interaccion/estado; recarga y persistencia si afecta |
| Contrato API | cliente/contrato y typecheck; handler backend y build si corresponde |
| Nueva superficie | typecheck, pruebas y build; vacio/carga/error/bloqueado y accesibilidad |
| CSS/tokens | build y revision de tokens; inspeccion visual ejecutada para cambios materiales |
| Accesibilidad | semantica, teclado y foco; inspeccion renderizada |
| Rendimiento/refactor | pruebas de comportamiento, typecheck y build; medida antes/despues para afirmar rendimiento |

Usar solo comandos reales y pertinentes; los nombres de gates no crean scripts. Build no demuestra interaccion; unitarias no demuestran integracion; screenshot no demuestra autoridad. Revalidar evidencia tras cambios. Si el arreglo exige efectos backend/canon/seguridad/release no autorizados, detener ese efecto y preparar handoff. Verificacion independiente requiere revisor distinto.
