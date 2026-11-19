---
name: bago5-private-mode
description: "Preparar una operación sensible con entrada privada controlada por el usuario y comprobación del efecto."
---

# Gestionar una operación sensible

Identifica quién debe introducir el dato y qué efecto autorizado requiere la aplicación. Averigua si el host ofrece una superficie privada de entrada que el agente no pueda leer. Comprueba dónde se procesan y almacenan los datos y si la interfaz adecuada está disponible.

Cuando la operación requiere un secreto, dirige al usuario a la interfaz oficial o al gestor local seleccionado. El usuario introduce allí el dato. Mantén credenciales, portapapeles, capturas, registros de consola y argumentos sensibles fuera del contexto compartido. Si no hay una ruta privada verificable, detén ese paso y declara su causa.

Tras devolver el control, comprueba únicamente señales no sensibles, por ejemplo que la aplicación autorizó la operación concreta o que el usuario cerró el diálogo. Entrega el estado de la acción y la evidencia mínima del efecto. Evita atribuir privacidad a un host solo porque se haya activado esta habilidad.
