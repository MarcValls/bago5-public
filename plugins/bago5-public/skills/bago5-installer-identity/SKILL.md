---
name: bago5-installer-identity
description: "Reparar una discrepancia de identidad entre programa instalado, manifiesto y versión mostrada."
---

# Verificar la identidad de instalación

Recoge el manifiesto de la candidata, la versión prevista, el comando normal de arranque y la salida real. Resuelve qué ejecutable selecciona el entorno y desde qué árbol carga sus recursos. Comprueba lanzadores alternativos si forman parte de la entrega.

Localiza dónde se obtiene el nombre y la versión. Corrige en la fuente autorizada la búsqueda del manifiesto relativo al ejecutable instalado. Si el manifiesto requerido falta o resulta inválido, muestra un error identificable. Conserva la política de compatibilidad de las versiones admitidas.

Construye la candidata y pruébala en un destino desechable. Inicia el programa desde un directorio distinto, compara su identidad con el manifiesto instalado y ensaya el fallo por manifiesto ausente sin alterar la instalación real. Entrega la identidad del binario, los archivos cambiados, huellas y resultados por punto de entrada.
