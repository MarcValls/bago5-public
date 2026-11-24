# Conexión de memoria seleccionada

Aplicar la [guía canónica del servicio ALIFE](../../bago5-memoria-viva/references/conexion-mcp.md).
BAGO5 funciona sin Sites y sin memoria remota. ALIFE PHP ofrece los destinos opcionales
`https://alifememories.com/mcp` y `https://alifememories.com/mcp/gestor`; comprobar
servicio, identidad, OAuth y scopes antes de configurarlos en el anfitrión.

No inferir permisos de una URL, instalación, correo validado ni referencia histórica.
No solicitar tokens en el chat ni crear Sites. Conectar solo el destino seleccionado,
conservar otras conexiones y verificar una lectura inocua sin escrituras de prueba.
