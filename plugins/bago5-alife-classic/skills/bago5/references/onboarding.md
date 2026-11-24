# Primer uso y recuperación de Memoria Viva

Guía a la persona en el cliente que está usando. Dale un solo paso y espera a saber qué ve. «Si quieres guardar algo para otra conversación, BAGO5 puede usar tu espacio privado en ALIFE». Si ya eligió una vía o ya tiene una memoria, empieza por ahí. Para una petición que funciona sin memoria, atiende la petición. Si pregunta por una habilidad, permite describir la tarea con sus palabras o usar el nombre anterior y consulta el catálogo y las rutas.

## Entrada desde el chat Classic

Usa el directorio web de [Plugins de ChatGPT](https://chatgpt.com/plugins) en la cuenta correspondiente para localizar BAGO5 Gobernado Classic. Una ficha privada requiere acceso de esa cuenta. Si el propio chat ya expone BAGO5, sigue allí directamente. Cuando falte la tarjeta alife_empezar, ofrece estas tres opciones en texto y espera la elección. Si la persona ya eligió una, continúa por esa vía.

## Primera elección

«¿Qué quieres hacer? 1. Crear mi primera memoria. 2. Conectar una que ya tengo. 3. Continuar sin memoria». Acepta el número o una respuesta en sus palabras.

1. **Crear mi primera memoria.** Pregunta cómo quiere llamarla. Abre o enlaza [Memoria Viva en ALIFE](https://alifememories.com/memoria-viva). Si necesita iniciar sesión, indica que introduzca su correo en el portal y confirme el enlace de un solo uso en ese navegador. Cuando vea sus espacios, guíala para introducir el nombre elegido y pulsar «Crear memoria». Si ese espacio ya aparece, permite seleccionarlo. Tras el alta, ofrece usarlo desde el chat.
2. **Conectar una memoria existente.** Si la persona pide comprobar su conexión, consulta la identidad y el permiso de lectura con el conector del cliente actual. Si corresponden al espacio elegido, confirma el resultado y sigue con su tarea. Si ha desconectado la cuenta en ChatGPT web, aplica el recorrido de reconexión. Continúa en el mismo chat Classic.
3. **Continuar sin memoria.** Pide la tarea o retoma la que ya indicó y trabaja en la conversación. Esta elección omite el acceso a ALIFE y la solicitud de correo.

## Reconectar desde el chat Classic

Si BAGO5 aparece en el selector del chat y faltan las herramientas de ALIFE, comprueba en los complementos instalados de esa cuenta si aparecen **ALIFE Memoria Viva nativa** y **ALIFE Gestor nativo**. Anota cuál falta. Una ficha privada visible para el creador puede requerir acceso en la cuenta de la persona que usa el chat. Atiende cada recurso por separado: la identidad del Gestor corresponde a la cuenta y `get_memory_identity` corresponde a la memoria seleccionada.

Comprueba el catálogo de ese chat antes de pedir otro consentimiento. Para lectura busca `get_memory`, para escritura `save_memory` o `patch_memory` y para archivos `get_vault_identity` y las operaciones de carga o descarga pertinentes. Informa por separado de las herramientas visibles y de los permisos efectivos. Usa los dos recursos nativos de `alifememories.com` declarados en el plugin. Si falta uno, conserva la tarea pendiente en ese destino.

- Indica que abra **Configuración → Aplicaciones** o **Plugins**, según la interfaz de su cuenta. Pregunta si ve **ALIFE Memoria Viva nativa**. Si falta, comprueba con ella la cuenta y el espacio de trabajo de ChatGPT y la disponibilidad de esa ficha. Mientras tanto puede abrir su memoria en el portal de ALIFE o continuar en el chat.
- Desde la ficha, guíala para conectar su cuenta. Si ALIFE solicita identificarse, se usa el correo de la cuenta que ya contiene la memoria. Después de confirmar en la otra pestaña, vuelve a la pestaña de autorización y pulsa «Continuar con mi cuenta».
- En «Autorizar conexión», pide que seleccione la memoria por su nombre y elija los permisos para la tarea. Para consultar basta la lectura. Si su memoria no aparece, revisa primero la cuenta de ALIFE. La reconexión reutiliza el espacio existente. La persona confirma pulsando «Autorizar».
- De vuelta en ese mismo chat, consulta `get_memory_identity`. Contrasta el espacio y el permiso efectivo con la elección del titular. Si hay un ID acordado, comprueba que coincide. Si la app está conectada pero falta lectura, distingue el permiso de la conexión de los «Permisos de acceso» de la memoria. Si el cliente carece de la herramienta, indica que la comprobación sigue pendiente.
- El correo y el consentimiento se gestionan en sus pantallas oficiales. Evita pedir contraseñas, enlaces de acceso o códigos en el chat. Una demostración usa datos ficticios y cero escrituras.

Al volver del consentimiento, comprueba la memoria con alife_conectar_memoria si está disponible, o con get_memory_identity. Informa del espacio y de los permisos que devuelve la aplicación. Para archivos, comprueba si el servidor ofrece get_vault_identity. Si lo ofrece, contrasta el mismo espacio, el almacenamiento y el permiso necesario. Si falta, explica «Tu memoria está conectada; esta conexión aún no ofrece archivos de Vault». Ofrece alife_conectar_vault únicamente si el servidor expone esa acción. La elección «Continuar sin memoria» sigue disponible desde el chat.
