"""Installed design parity and report-first/standalone delivery, no model calls."""
import copy
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'reading-yearbook-skill/scripts'))
from reading_delivery import deliver, read_report, preview_server
from build_reading_html import build_html
from test_report_reader import bundle, report_data
import skill_release


class DeliveryTests(unittest.TestCase):
    def test_preview_reuses_origin_after_restart_and_handles_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'index.html';path.write_text('<h1>受控示例</h1>','utf-8')
            first=preview_server(path);port=first.server_port
            second=preview_server(path)
            try:self.assertNotEqual(second.server_port,port)
            finally:second.server_close();first.server_close()
            reopened=preview_server(path)
            try:self.assertEqual(reopened.server_port,port)
            finally:reopened.server_close()

    def test_append_update_preserves_annual_data_and_other_books(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'index.html'
            build_html(report_data(), path)
            before = read_report(path)
            first, second = bundle(title='第一本'), bundle(title='第二本')
            deliver(path, path, [first])
            deliver(path, path, [second])
            deliver(path, path, [first])
            after = read_report(path)
            self.assertEqual(after['distillations'], [first, second])
            for key in ('year', 'summary', 'books', 'features'):
                self.assertEqual(before.get(key), after.get(key))

    def test_refresh_preserves_prior_distillations(self):
        import generate_reading_html as generator
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'index.html'
            previous = report_data([bundle()])
            snapshot = {'year': 2026, 'as_of': '2026-11-15', 'shelf': {'books': []},
                        'annual': {'readStat': [{'stat': '读过', 'counts': '0本'}], 'readLongest': []}}
            generator.deliver(snapshot, {'year': 2026, 'books': []}, {}, path, previous=previous)
            self.assertEqual(read_report(path)['distillations'], previous['distillations'])

    def test_invalid_bundle_never_overwrites_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'index.html'
            build_html(report_data(), path)
            old = path.read_bytes()
            bad = bundle(); bad['analysis']['overview'] = '篡改'
            with self.assertRaises(ValueError):
                deliver(path, path, [bad])
            self.assertEqual(path.read_bytes(), old)
            with self.assertRaises(ValueError):
                deliver(path, path, [bundle(sample=True)])
            self.assertEqual(path.read_bytes(), old)

    def test_standalone_contains_current_reader_and_no_annual_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'book.html'
            deliver(path, packages=[bundle()])
            html = path.read_text('utf8')
            self.assertIn('ebook-standalone', html)
            self.assertIn('蒸馏一本书', html)
            self.assertIn('position:sticky', html)
            self.assertNotIn('id="reading-data"', html)
            self.assertNotIn('id="ebookShareToggle"', html)

    def test_fresh_install_generates_identical_report(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); installed = root/'installed'
            skill_release.install(installed)
            source = root/'data.json'
            source.write_text(json.dumps(report_data([bundle()]), ensure_ascii=False), 'utf8')
            outputs = []
            # Compare package parity under the same dependency versions. The
            # developer checkout may use .vendor while the clean install uses
            # global packages; different fontTools versions encode differently.
            environment = dict(os.environ)
            vendor = ROOT/'reading-yearbook-skill/.vendor'
            if vendor.is_dir():
                environment['PYTHONPATH'] = str(vendor) + os.pathsep + environment.get('PYTHONPATH', '')
            for index, scripts in enumerate((ROOT/'reading-yearbook-skill/scripts', installed/'scripts')):
                target = root/('report'+str(index)+'.html')
                subprocess.run([sys.executable, '-X', 'utf8', str(scripts/'build_reading_html.py'), '--input', str(source), '--output', str(target)], check=True, capture_output=True, env=environment)
                outputs.append(target.read_bytes())
            self.assertEqual(outputs[0], outputs[1])
            self.assertTrue((installed/'scripts/reading_delivery.py').is_file())
            self.assertTrue((installed/'references/standard-delivery.md').is_file())

    def test_preview_only_exposes_selected_html_and_reads_updates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'index.html';path.write_text('<h1>报告</h1>', 'utf8')
            (Path(tmp)/'private.json').write_text('private', 'utf8')
            server = preview_server(path)
            worker = threading.Thread(target=server.serve_forever, daemon=True);worker.start()
            url = 'http://127.0.0.1:'+str(server.server_port)
            try:
                self.assertIn('报告', urlopen(url).read().decode())
                path.write_text('<h1>更新</h1>', 'utf8')
                self.assertIn('更新', urlopen(url).read().decode())
                for tail in ('/private.json', '/%2e%2e/private.json', '/api/jobs'):
                    with self.assertRaises(HTTPError):
                        urlopen(url+tail)
            finally:
                server.shutdown();server.server_close();worker.join()


if __name__ == '__main__':
    unittest.main()

