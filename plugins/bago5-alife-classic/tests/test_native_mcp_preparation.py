import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_preparation', ROOT / 'scripts/prepare_native_mcp.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class PreparationTests(unittest.TestCase):
    def response(self, url, method='GET'):
        origin = native.ORIGIN
        if url.endswith('/.well-known/oauth-authorization-server'):
            return 200, {}, {'issuer': origin, 'authorization_endpoint': origin+'/oauth/authorize',
                'token_endpoint': origin+'/oauth/token',
                'code_challenge_methods_supported': ['S256'], 'grant_types_supported': ['authorization_code'],
                'token_endpoint_auth_methods_supported': ['none']}
        path = '/mcp/gestor' if url.endswith('/mcp/gestor') else '/mcp'
        if method == 'GET':
            return 200, {}, {'resource': origin+path, 'authorization_servers': [origin],
                'scopes_supported': ['manager.read', 'manager.write', 'catalog.admin'] if path.endswith('gestor') else ['memory.read', 'memory.write']}
        return 401, {'www-authenticate': f'Bearer resource_metadata="{origin}/.well-known/oauth-protected-resource{path}"'}, {'error':'invalid_token'}

    def test_preparation_is_optional_and_does_not_claim_authenticated_access(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'mcp.json'
            active_before = (ROOT/'mcp.json').read_bytes()
            result = native.prepare(path, self.response)
            config = json.loads(path.read_text())
            self.assertEqual(config, json.loads(active_before))
            self.assertEqual(set(config['mcpServers']), {'alife-gestor-nativo', 'alife-memoria-viva'})
            self.assertEqual(result['discovery']['alife-memoria-viva']['catalog'], 'AUTH_REQUIRED')
            self.assertFalse(result['authenticated_host_connection'])
            self.assertEqual(result['client_registration'], 'NOT_RUN')
            self.assertEqual((ROOT/'mcp.json').read_bytes(), active_before)

    def test_readonly_preflight_does_not_contact_mail_registration_or_private_content(self):
        calls = []
        def fetch(url, method):
            calls.append((url, method))
            return self.response(url, method)
        native.prepare(None, fetch)
        self.assertEqual(len(calls), 5)
        self.assertTrue(all(method=='GET' or url in (native.ORIGIN+'/mcp', native.ORIGIN+'/mcp/gestor') for url,method in calls))
        self.assertFalse(any(url.endswith('/oauth/register') or '/auth/' in url for url,_ in calls))

    def test_wrong_issuer_or_incompatible_public_client_cannot_prepare_config(self):
        for mutate in [lambda obj: obj.pop('authorization_endpoint'), lambda obj: obj.update(issuer='https://other.example'),
                       lambda obj: obj.update(token_endpoint_auth_methods_supported=['client_secret_basic']),
                       lambda obj: obj.update(code_challenge_methods_supported=['plain'])]:
            with self.subTest(mutation=mutate), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)/'mcp.json'
                def fetch(url, method):
                    status, headers, body = self.response(url, method)
                    if 'issuer' in body: mutate(body)
                    return status, headers, body
                with self.assertRaises(native.NotReady): native.prepare(path, fetch)
                self.assertFalse(path.exists())

    def test_wrong_resource_or_legacy_permissions_block_preparation(self):
        for mutate in [lambda obj: obj.update(resource=native.ORIGIN+'/mcp'),
                       lambda obj: obj.update(scopes_supported=['manager.write'])]:
            with self.subTest(mutation=mutate):
                def fetch(url, method):
                    status, headers, body = self.response(url, method)
                    if method=='GET' and url.endswith('/mcp/gestor'): mutate(body)
                    return status, headers, body
                with self.assertRaises(native.NotReady): native.prepare(None, fetch)

    def test_redirect_throttling_or_unavailable_metadata_stops_without_retry(self):
        for status in [302,403,429,503]:
            calls=[]
            def fetch(url, method): calls.append(url); return status, {}, {}
            with self.subTest(status=status), self.assertRaises(native.NotReady): native.prepare(None, fetch)
            self.assertEqual(len(calls), 1)
        self.assertIsNone(native.NoRedirect().redirect_request(None,None,302,'',{},'https://other.example'))

    def test_anonymous_success_or_wrong_challenge_does_not_prove_protected_endpoint(self):
        for status,headers in [(200,{}),(401,{'www-authenticate':'Bearer resource_metadata="https://other.example"'})]:
            def fetch(url, method):
                return (status, headers, {'error':'invalid_token'}) if method=='POST' else self.response(url, method)
            with self.subTest(status=status), self.assertRaises(native.NotReady): native.prepare(None, fetch)

    def test_public_memory_catalog_is_metadata_only(self):
        for cursor, expected in [(None, 'COMPLETE'), ('next', 'FIRST_PAGE')]:
            def fetch(url, method):
                if method == 'POST' and url == native.ORIGIN + '/mcp':
                    result = {'tools': [{'name': 'get_vault_identity'}], 'nextCursor': cursor}
                    return 200, {}, {'jsonrpc': '2.0', 'id': 1, 'result': result}
                return self.response(url, method)
            result = native.prepare(None, fetch)
            catalog = result['discovery']['alife-memoria-viva']
            self.assertEqual(catalog['catalog'], expected)
            self.assertEqual(catalog['tool_names'], ['get_vault_identity'])
            self.assertFalse(result['authenticated_host_connection'])

    def test_memory_catalog_error_or_missing_write_scope_is_reported(self):
        for fail_method in ['GET', 'POST']:
            def fetch(url, method):
                status, headers, body = self.response(url, method)
                if url.endswith('/mcp') and method == fail_method:
                    if method == 'POST':
                        return 200, {}, {'jsonrpc': '2.0', 'id': 1, 'error': {'code': -32601}}
                    body['scopes_supported'] = ['memory.read']
                return status, headers, body
            with self.subTest(method=fail_method), self.assertRaises(native.NotReady):
                native.prepare(None, fetch)

    def test_existing_configuration_is_preserved_without_contacting_server(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'mcp.json';path.write_text('existing connection')
            with self.assertRaises(native.NotReady): native.prepare(path, lambda *_: self.fail('network must not run'))
            self.assertEqual(path.read_text(), 'existing connection')

    def test_active_plugin_cannot_be_changed_by_preparation(self):
        with self.assertRaises(native.NotReady):
            native.prepare(ROOT/'mcp.json', lambda *_: self.fail('network must not run'))

    def test_drift_in_authentication_is_not_copied_after_endpoint_preflight(self):
        for replacement in [{'type':'none'}, {'type':'oauth','client':{'mode':'dcr'},'baseScopes':['catalog.admin']}]:
            with self.subTest(auth=replacement), tempfile.TemporaryDirectory() as directory:
                candidate=Path(directory)/'candidate.json';output=Path(directory)/'mcp.json'
                config=json.loads(native.CANDIDATE.read_text())
                config['mcpServers']['alife-gestor-nativo']['extensions']['com.openai']['auth']=replacement
                candidate.write_text(json.dumps(config))
                with patch.object(native, 'CANDIDATE', candidate), self.assertRaises(native.NotReady):
                    native.prepare(output, self.response)
                self.assertFalse(output.exists())


if __name__=='__main__': unittest.main()
