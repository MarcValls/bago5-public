---
name: bago5-installer-sync
description: "Sincronizar fuente, instalador y distribución de una misma candidata con comprobaciones de instalación y recuperación."
---

# Sincronizar un instalador

Establece la versión y la fuente de autoridad. Inventaría por separado árbol de trabajo, manifiesto, archivo de distribución, lanzador de instalación y copia instalada. Anota las diferencias de contenido que sí están previstas.

Aplica los cambios en una copia escribible y verifica primero el instalador con un destino temporal vacío. Ensaya actualización sobre la versión admitida y comprueba qué ocurre con datos y configuración del usuario. Verifica que el instalador puede recuperarse ante un fallo parcial. Si debe descargar archivos, valida la identidad de la carga antes de aplicar cambios.

Compara versiones y hashes de los componentes que deben coincidir. Si la tarea incluye publicar o sustituir una instalación, comprueba destino y autorización y relee su estado tras la operación. Entrega tabla de origen, empaquetado, instalación ensayada e instalación efectiva, con pasos de vuelta atrás.
