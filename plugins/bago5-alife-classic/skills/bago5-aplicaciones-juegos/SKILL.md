---
name: bago5-aplicaciones-juegos
description: "Desarrolla, revisa y prepara aplicaciones o juegos con las herramientas y la tecnología del proyecto."
---

Aplicar una sola vez por misión el ciclo vigente de [bago5-ganchos-sesion](../bago5-ganchos-sesion/SKILL.md) y su [contrato de continuidad](../bago5-ganchos-sesion/references/lifecycle.md); en las derivaciones, reutilizar el binding y estado actuales de proyecto, sesión y memoria. Revisar después únicamente los controles pertinentes al evento y a la tarea, sin reinicializar el ciclo ni recorrer dependencias recursivas. Este enlace no activa todos los especialistas ni autoriza efectos, archivos, persistencia o instalación de hooks; cada operación conserva sus requisitos de alcance, herramientas y autorización vigentes.

Antes de fijar o preparar una versión, runtime o configuración para un destino, o ejecutar una acción que dependa de ellos, aplicar la [comprobación previa del destino](../bago5/references/target-preflight.md); si falta evidencia actual, bloquear solo el trabajo dependiente y continuar lo independiente.

# Desarrollo de aplicaciones y juegos

Cuando el encargo sea crear o ampliar aplicaciones o herramientas del producto
BAGO5, aplicar [desarrollo nativo en ALIFE](../bago5/references/native-tool-development.md).
ALIFE y Memoria Viva son las aplicaciones del producto sobre la infraestructura
de `alifememories.com`; reutilizar su backend PHP/MariaDB, interfaz y conexiones MCP.
La creación de otra Memoria Viva aprovisiona un espacio de datos de la cuenta,
sin generar un Site ni instalar una aplicación por cada memoria.

Para un encargo expresamente dirigido a un proyecto de ChatGPT Sites, aplicar
también `bago5-alineacion-fuentes-sites` antes de editar y al cerrar, aunque Sites
no exponga una shell. No elegir ese destino por disponer de sus herramientas.
Conservar las fuentes Sites históricas de ALIFE como procedencia o material de
migración, sin editarlas como parte del flujo nativo. No usar una página publicada
como sustituto de sus fuentes. Si el chat carece de escritura, entregar «Sugerencias
de cambios» con rutas y diff propuesto, distinguiendo propuesta e implementación.

Respeta plataforma, motor, stack, alcance y lenguaje elegidos por el usuario. Una pregunta o inspección menor no requiere crear una misión, ejecutar builds o lanzar pruebas. Para auditoría, sigue el comportamiento desde el entrypoint hasta el runtime real. Para implementación, inspecciona el proyecto e instrucciones y elige el cambio completo más pequeño.

No deduzcas que SDK, motor, navegador, simulador, device, plugin o MCP está disponible por un nombre o archivo. Comprueba las herramientas actuales. Si una falta, continúa con trabajo de fuente útil y deja la comprobación runtime NOT_RUN.

Antes de un cambio material registra baseline y propiedades que deben preservarse cuando el proyecto lo permita. Mantén dominio, presentación, persistencia y adaptadores proporcionados a la necesidad real; usa herramientas estándar del stack antes de añadir dependencias. No ejecutes comandos del proyecto por iniciativa propia; ejecútalos cuando el usuario los solicite o el alcance activo los autorice expresamente.

Para verificar, elige el límite correcto: lint/type check, build, lanzamiento de app o flujo jugable. No confundas build con gameplay validado ni screenshot con estados no observados. Liga los resultados a la candidata, plataforma y runtime exactos. Publicar, desplegar, comprar recursos, instalar software o cambios destructivos requieren autorización aparte.

Al entregar instaladores, lanzadores o pruebas de un proceso repetible, seguir [entrega guiada](../bago5/references/entrega-guiada.md), adaptando nombres y pasos al stack y la plataforma. Comprobar secuencia y estado real sin presentar instalación no ejecutada como completada.

En Codex, aplica el [formato de respuesta de BAGO](../bago5/SKILL.md#respuestas-en-codex) al comunicar el resultado.
