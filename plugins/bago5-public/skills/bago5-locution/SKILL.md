---
name: bago5-locution
description: "Leer un texto en voz alta usando un receptor de voz local autorizado y distinguir recepción y reproducción."
---

# Leer en voz alta

Resuelve el texto exacto solicitado. Si se refiere a una respuesta anterior, recupera esa respuesta antes de leer. Mantén idioma y orden. Para una lectura literal, conserva el contenido y divide solo si lo exige el receptor.

Comprueba si el host ofrece reproducción o un receptor local elegido por el usuario. Selecciona la voz y velocidad admitidas. Envía el texto por ese canal y registra el estado devuelto. Ante una respuesta incierta, consulta la cola antes de repetir para evitar leer dos veces. Mantén micrófono y almacenamiento de audio fuera de esta operación.

Informa por separado de texto preparado, solicitud recibida y reproducción confirmada por el dispositivo. Si el receptor está desconectado, entrega el texto y la causa de `NOT_RUN`. Un recibo de cola confirma entrega al receptor.
