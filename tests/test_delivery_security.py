"""Security boundaries with synthetic credentials; no remote account requests."""
import os
import re
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'reading-yearbook-skill/scripts'))
from output_security import ensure_no_credentials
from reading_delivery import preview_server, deliver
from report_reader import safe_json
from collect_weread_data import gateway_call, WeReadError, _unwrap
from collect_html_materials import validate_cover_url


class DeliverySecurityTests(unittest.TestCase):
    def test_active_key_and_key_format_rejected_without_echo(self):
        for key in ('synthetic-live-key-123456', 'wrk-security-test-123456'):
            with patch.dict(os.environ, {'WEREAD_API_KEY': key}):
                for check in (ensure_no_credentials, safe_json):
                    with self.assertRaises(ValueError) as error:
                        check({'overview': 'accidentally pasted: ' + key})
                    self.assertNotIn(key, str(error.exception))

    def test_failed_report_delivery_preserves_original(self):
        from test_reading_html import fixture
        from build_reading_html import build_html, adapt_data
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'index.html'; target.write_text('original', 'utf-8')
            data = adapt_data(fixture())
            data['books'][0]['title'] = 'wrk-security-test-123456'
            with self.assertRaises(ValueError):
                build_html(data, target)
            self.assertEqual(target.read_text('utf-8'), 'original')

    def test_cover_urls_reject_credentials_and_nonstandard_ports(self):
        validate_cover_url('https://cdn.weread.qq.com/cover.jpg')
        for url in ('http://cdn.weread.qq.com/x', 'https://cdn.weread.qq.com:8443/x',
                    'https://user:password@cdn.weread.qq.com/x', 'https://127.0.0.1/x',
                    'https://cdn.weread.qq.com.evil.invalid/x'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_cover_url(url)

    def test_gateway_redirect_stops_before_second_request(self):
        paths = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                paths.append(self.path)
                self.send_response(302); self.send_header('Location', '/credential-target'); self.end_headers()
            def do_GET(self):
                paths.append(self.path)
                self.send_response(200); self.end_headers(); self.wfile.write(b'{}')
            def log_message(self, *_): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        try:
            url = 'http://127.0.0.1:' + str(server.server_port) + '/gateway'
            with patch('collect_weread_data.GATEWAY_URL', url), self.assertRaises(WeReadError) as error:
                gateway_call('/shelf/sync', {}, 'synthetic-credential', retries=0)
            self.assertEqual(paths, ['/gateway'])
            self.assertNotIn('synthetic-credential', str(error.exception))
        finally:
            server.shutdown(); server.server_close(); worker.join()

    def test_remote_upgrade_message_is_not_echoed(self):
        with self.assertRaises(WeReadError) as error:
            _unwrap({'upgrade_info': {'message': 'credential: synthetic-sensitive-value'}})
        self.assertNotIn('synthetic-sensitive-value', str(error.exception))

    def test_standalone_and_bundle_do_not_bypass_credential_guard(self):
        from serve_ebook import offline_page
        from distillation_result import validate_bundle
        from test_report_reader import bundle
        key = 'wrk-security-test-123456'
        with self.assertRaises(ValueError):
            offline_page({}, key)
        value = bundle(); value['analysis']['overview'] = key
        with self.assertRaises(ValueError) as error:
            validate_bundle(value)
        self.assertNotIn(key, str(error.exception))

    def test_preview_security_headers_cross_site_and_updated_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'index.html'; target.write_text('<h1>safe</h1>', 'utf-8')
            server = preview_server(target, 0)
            worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
            url = 'http://127.0.0.1:' + str(server.server_port)
            opener = build_opener(ProxyHandler({}))
            try:
                with opener.open(url) as response:
                    self.assertEqual(response.headers['Referrer-Policy'], 'no-referrer')
                    self.assertEqual(response.headers['X-Frame-Options'], 'DENY')
                    self.assertIn("connect-src 'none'", response.headers['Content-Security-Policy'])
                for headers in ({'Origin':'https://other.invalid'}, {'Host':'other.invalid'},
                                {'Sec-Fetch-Site':'cross-site','Sec-Fetch-Mode':'no-cors'}):
                    with self.assertRaises(HTTPError) as error:
                        opener.open(Request(url, headers=headers))
                    self.assertEqual(error.exception.code, 403)
                target.write_text('wrk-security-test-123456', 'utf-8')
                with self.assertRaises(HTTPError) as error:
                    opener.open(url)
                self.assertEqual(error.exception.code, 503)
                self.assertNotIn(b'wrk-security-test', error.exception.read())
            finally:
                server.shutdown(); server.server_close(); worker.join()

    def test_readme_links_format_and_docs_scope(self):
        text = (ROOT / 'README.md').read_text('utf-8')
        self.assertNotIn('*', text)
        prose = re.sub(r'```.*?```', '', text, flags=re.S)
        self.assertNotRegex(prose, r'[\u4e00-\u9fff] +[A-Za-z0-9\u4e00-\u9fff]')
        for path in re.findall(r'\]\(([^)]+)\)', text):
            if not path.startswith(('https://', 'http://', '#')):
                self.assertTrue((ROOT / path).exists(), path)
        self.assertEqual({p.relative_to(ROOT / 'docs').as_posix() for p in (ROOT / 'docs').rglob('*.md')},
                         {'architecture.md', 'testing.md'})
