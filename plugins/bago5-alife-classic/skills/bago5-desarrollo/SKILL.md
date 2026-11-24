---
name: bago5-desarrollo
description: "Implementa cambios autorizados y comprueba su resultado, preservando capacidades, contratos y compatibilidad."
---

Aplicar una sola vez por misión el ciclo vigente de [bago5-ganchos-sesion](../bago5-ganchos-sesion/SKILL.md) y su [contrato de continuidad](../bago5-ganchos-sesion/references/lifecycle.md); en las derivaciones, reutilizar el binding y estado actuales de proyecto, sesión y memoria. Revisar después únicamente los controles pertinentes al evento y a la tarea, sin reinicializar el ciclo ni recorrer dependencias recursivas. Este enlace no activa todos los especialistas ni autoriza efectos, archivos, persistencia o instalación de hooks; cada operación conserva sus requisitos de alcance, herramientas y autorización vigentes.

Antes de fijar o preparar una versión, runtime o configuración para un destino, o ejecutar una acción que dependa de ellos, aplicar la [comprobación previa del destino](../bago5/references/target-preflight.md); si falta evidencia actual, bloquear solo el trabajo dependiente y continuar lo independiente.

# #BAGO5-development · Implementación controlada

Aplicar cambios solo con alcance concreto y permisos efectivos. Primero recuperar baseline, contratos, invariantes, aceptación y fuente canónica vigente. Reutilizar componentes estables; no inventar módulos ante una capacidad existente.

Para crear o ampliar herramientas y aplicaciones del producto BAGO5, aplicar
[desarrollo nativo en ALIFE](../bago5/references/native-tool-development.md).
La implementación principal se añade al repositorio de `alifememories.com`, en el
servidor PHP/MariaDB existente y la superficie MCP que corresponda. ALIFE gestiona
cuentas y memorias; Memoria Viva opera el contenido de la memoria autorizada.
Las skills describen su uso. Un descriptor MCP, una skill o una ficha de catálogo
no sustituyen al handler, sus permisos, su despliegue ni la conexión del anfitrión.
No crear o modificar Sites como paso implícito de este desarrollo ni como solución
a una capacidad nativa ausente. Para otro proyecto, conservar el stack y destino
que ese proyecto tenga autorizados.

Para cambios no triviales: capacidad → contrato → schema → vectores → tests/verificadores → evidencia → candidata → comparación diferencial. Si faltan herramientas/permiso, entregar candidato o comandos `NOT_RUN`, no afirmar implementación.

Preservar capacidades anteriores, historial de decisiones, datos, integraciones, funciones y UX. Registrar cualquier decisión adoptada, incluso pequeña; cuando se implementa, mantener histórico sin elevarla automáticamente a verificada.

Producir lista concreta de artefactos modificados, diff, pruebas realizadas, fallos, regresiones y límites. Remitir a `VERIFICATION` una candidata identificable sin afirmar revisión independiente.

Para procesos repetibles entregados como scripts o paquetes aplicar [entrega guiada](../bago5/references/entrega-guiada.md): batería inicial numerada, pasos secuenciales y siguiente acción visible, con pruebas y efectos ajustados al entorno autorizado.
