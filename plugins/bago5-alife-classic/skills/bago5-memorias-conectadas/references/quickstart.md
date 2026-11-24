# Uso local — paquete independiente, Windows PowerShell y Python

## Qué instala y qué no

La skill lleva un backend **local opcional** ejecutable con Python 3.10+ estándar y SQLite. No incluye Site remoto, certificado TLS, cliente OAuth, registro MCP ni conexión automática a ChatGPT. Ejecutar el script es una acción explícita, nunca implícita por haber instalado el plugin.

**Seguridad:** la demo es exclusivamente `127.0.0.1`; no publicar el puerto en Internet. El fichero SQLite incluye recuerdos: guardarlo en un directorio privado y protegerlo mediante permisos del SO y copias locales cifradas según necesidad. Los tokens de cuenta se muestran una vez al crearlos; no guardar tokens en Git, ZIP, conversaciones, memoria, líneas de comandos ni capturas. Se admiten variables de entorno de la sesión.

## Arranque paso a paso

Desde la carpeta que contiene la skill:

```powershell
$hub = '.\\skills\\bago5-memorias-conectadas\\scripts\\mv_hub.py'
py -3 $hub --help
py -3 $hub user-add alice
# Guardar el token devuelto en un gestor seguro e incorporarlo a la sesión sin publicarlo.
$env:BAGO5_MV_TOKEN = Read-Host 'Token de alice'
py -3 $hub store-add 'Memoria privada'
# Usar el store_id devuelto, por ejemplo:
# py -3 $hub project-add <STORE_ID> 'Proyecto A'
py -3 $hub serve --port 8765
```

En otra PowerShell local, con token obtenido por canal autorizado:

```powershell
$headers = @{ Authorization = ('Bearer ' + $env:BAGO5_MV_TOKEN) }
Invoke-RestMethod http://127.0.0.1:8765/stores -Headers $headers
Invoke-RestMethod http://127.0.0.1:8765/connections -Headers $headers
```

Para invitar a otro usuario local previamente dado de alta por el administrador (`user-add bob`), realizar POST `/invitations` autenticado como dueño, con `store_id`, `project_id`, `recipient_id`, `role` y `hours`. El destinatario, autenticado con su propia cuenta, acepta mediante `/invitations/accept` con `invitation_id` y `invitation_secret`. El dueño revoca vía `/invitations/revoke`. No pasar el secreto de invitación por mensajes públicos.

## Paquetes ZIP

```powershell
# Exportar un almacén propio a una ruta NUEVA
py -3 $hub export <STORE_ID_ORIGEN> .\\memoria_exportada.zip
# Vista previa de importación, sin escribir
py -3 $hub import <STORE_ID_DESTINO> .\\memoria_exportada.zip
# Solo tras revisar y aceptar el destino
py -3 $hub import <STORE_ID_DESTINO> .\\memoria_exportada.zip --commit
```

La exportación es **del Hub SQLite local**, no de cualquier Site remoto. Importar requiere propiedad del almacén destino; un editor compartido no puede introducir un paquete de terceros. La escritura de importación es atómica y se niega ante conflictos en vez de sobrescribir.

## Conexiones múltiples

POST `/connections` autenticado con `{ "alias":"memoria-general", "endpoint":"https://example.test/mcp", "expected_identity":"id-comprobable" }` y POST `/connections/select` con `{ "alias":"memoria-general" }`.

Se guarda en SQLite por usuario, sin credenciales. El estado de un alias permanece `UNVERIFIED` porque esta API **no hace negociación OAuth ni llama MCP**. El plugin debe descubrir y verificar por separado los conectores que el host realmente exponga.

## Pruebas reproducibles

```powershell
py -3 -m unittest discover -s .\\skills\\bago5-memorias-conectadas\\tests -v
```

No se necesita red externa. Hay pruebas positivas y negativas de ACL, identidad del invitado, revocación, expiración, conflicto de versión, reimportación, integridad, privacidad de campos y API HTTP local.
