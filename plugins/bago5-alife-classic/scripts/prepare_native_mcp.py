#!/usr/bin/env python3
"""Inspect public native endpoints and optionally prepare a new portable MCP file.

Never registers a client, requests mail, authenticates, reads user data, follows
redirects or changes the active plugin. A 401 checks the boundary, not host access.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

ORIGIN = 'https://alifememories.com'
ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / 'integrations/alife/mcp.candidate.json'
SERVERS = {
    'alife-gestor-nativo': ('/mcp/gestor', 'bago5-chatgpt-gestor', ['manager.read']),
    'alife-memoria-viva': ('/mcp', 'bago5-chatgpt-memoria', ['memory.read', 'memory.write']),
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class NotReady(ValueError):
    pass


def request(url: str, method: str = 'GET') -> tuple[int, dict, object]:
    headers = {'Accept': 'application/json, text/event-stream', 'User-Agent': 'BAGO5-native-preflight/1.0'}
    data = None
    if method == 'POST':
        headers['Content-Type'] = 'application/json'
        data = b'{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
    try:
        response = build_opener(NoRedirect()).open(Request(url, data=data, headers=headers, method=method), timeout=12)
    except HTTPError as exc:
        response = exc
    with response:
        status = response.status
        response_headers = {key.lower(): value for key, value in response.headers.items()}
        raw = response.read(65537)
    if len(raw) > 65536:
        raise NotReady('Respuesta pública demasiado grande.')
    if 'application/json' not in response_headers.get('content-type', '').lower():
        raise NotReady(f'HTTP {status}: no se recibió JSON del servicio nativo.')
    try:
        body = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise NotReady('Respuesta JSON inválida.') from exc
    return status, response_headers, body


def inspect(fetch=request) -> dict:
    checks = []

    def metadata(path):
        status, _, body = fetch(ORIGIN + path, 'GET')
        if status != 200 or not isinstance(body, dict):
            raise NotReady(f'{path}: HTTP {status}, metadatos no disponibles.')
        return body

    auth = metadata('/.well-known/oauth-authorization-server')
    for field, suffix in {'issuer': '', 'authorization_endpoint': '/oauth/authorize',
                          'token_endpoint': '/oauth/token'}.items():
        if auth.get(field) != ORIGIN + suffix:
            raise NotReady(f'{field}: identidad o registro OAuth no comprobado.')
    for field, value in [('code_challenge_methods_supported', 'S256'),
                         ('grant_types_supported', 'authorization_code'),
                         ('token_endpoint_auth_methods_supported', 'none')]:
        if not isinstance(auth.get(field), list) or value not in auth[field]:
            raise NotReady(f'{field}: capacidad OAuth requerida ausente.')
    checks.append('native_oauth_discovery')
    discovery = {}
    for name, (path, _, scopes) in SERVERS.items():
        meta_path = '/.well-known/oauth-protected-resource' + path
        resource = metadata(meta_path)
        if resource.get('resource') != ORIGIN + path or resource.get('authorization_servers') != [ORIGIN]:
            raise NotReady(f'{path}: identidad del recurso no coincide.')
        supported = resource.get('scopes_supported')
        if not isinstance(supported, list) or not all(isinstance(v, str) for v in supported) or not set(scopes).issubset(supported):
            raise NotReady(f'{path}: faltan permisos del contrato nativo.')
        status, headers, body = fetch(ORIGIN + path, 'POST')
        challenge = headers.get('www-authenticate', '')
        observation = {'scopes_supported': supported, 'tools_list_http': status}
        if status == 401 and isinstance(body, dict) and body.get('error') == 'invalid_token' and f'resource_metadata="{ORIGIN}{meta_path}"' in challenge:
            observation['catalog'] = 'AUTH_REQUIRED'
        elif path == '/mcp' and status == 200:
            if not isinstance(body, dict) or body.get('jsonrpc') != '2.0' or body.get('id') != 1 or 'error' in body:
                raise NotReady(f'{path}: respuesta tools/list inválida.')
            result = body.get('result')
            tools = result.get('tools') if isinstance(result, dict) else None
            if not isinstance(tools, list) or not all(isinstance(t, dict) and isinstance(t.get('name'), str) and t['name'] for t in tools):
                raise NotReady(f'{path}: catálogo tools/list inválido.')
            observation['catalog'] = 'FIRST_PAGE' if result.get('nextCursor') else 'COMPLETE'
            observation['tool_names'] = sorted(t['name'] for t in tools)
        else:
            raise NotReady(f'{path}: respuesta inesperada al descubrimiento MCP (HTTP {status}).')
        discovery[name] = observation
        checks.append(path)
    return {'state': 'ENDPOINTS_CHECKED', 'origin': ORIGIN, 'checks': checks, 'discovery': discovery,
            'authenticated_host_connection': False, 'user_memory_access': 'NOT_RUN',
            'client_registration': 'NOT_RUN', 'side_effects': 'none; public metadata and unauthenticated tool-list requests only'}


def prepare(output: Path | None, fetch=request) -> dict:
    if output is not None:
        if output.resolve().is_relative_to(ROOT):
            raise NotReady('Prepara la candidata fuera del plugin activo; su publicación es un paso posterior.')
        if output.exists() or output.is_symlink():
            raise NotReady('El destino ya existe; no se sobrescribe una configuración.')
    result = inspect(fetch)
    config = json.loads(CANDIDATE.read_text(encoding='utf-8'))
    if not isinstance(config, dict):
        raise NotReady('La configuración candidata no es un objeto.')
    servers = config.get('mcpServers', {})
    if not isinstance(servers, dict) or set(servers) != set(SERVERS) or config.get('$schema') != 'https://agent-plugins.org/schemas/1.0.0/mcp.schema.json':
        raise NotReady('La configuración candidata no corresponde a las dos aplicaciones comprobadas.')
    for name, (suffix, client_id, defaults) in SERVERS.items():
        server = servers[name]
        if not isinstance(server, dict) or set(server) != {'type','url','extensions'} or server.get('type') != 'streamable-http' or server.get('url') != ORIGIN + suffix:
            raise NotReady('La configuración candidata apunta a un servidor distinto del comprobado.')
        client = {'mode': 'provided', 'clientId': client_id, 'tokenEndpointAuthMethod': 'none'}
        expected = {'com.openai': {'auth': {'type': 'oauth', 'client': client,
                                           'baseScopes': defaults[:1], 'defaultScopes': defaults}}}
        if server['extensions'] != expected:
            raise NotReady('La autenticación candidata no coincide con el contrato comprobado.')
    if output is not None:
        # Exclusive creation also rejects a racing writer or an existing symlink.
        with output.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(config, ensure_ascii=False, indent=2) + '\n')
        result['prepared_file'] = str(output.resolve())
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Archivo nuevo que se preparará solo tras verificar los endpoints; no publica ni conecta el plugin.')
    args = parser.parse_args(argv)
    try:
        print(json.dumps(prepare(args.output), ensure_ascii=False, indent=2))
        return 0
    except (NotReady, OSError, URLError) as exc:
        print(json.dumps({'state': 'BLOCKED', 'reason': str(exc), 'authenticated_host_connection': False}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
