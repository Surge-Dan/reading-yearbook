import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'reading-yearbook-skill/scripts'))
from html_assembly import insert_before_closing_tag
from skill_release import manifest, file_hash


class PortabilityTests(unittest.TestCase):
    def test_extensionless_licenses_are_text_across_windows_checkout(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('LICENSE', 'NOTICE', 'COPYING'):
                path = root/name;path.write_bytes(b'License\nPermission\n')
                record = next(x for x in manifest(root)['files'] if x['path'] == name)
                self.assertEqual(record['hash_kind'], 'text-lf')
                path.write_bytes(b'License\r\nPermission\r\n')
                self.assertEqual(file_hash(path, record['hash_kind']), record['sha256'])
                path.write_bytes(b'Changed\r\nPermission\r\n')
                self.assertNotEqual(file_hash(path, record['hash_kind']), record['sha256'])

    def test_assembly_does_not_inject_into_script_or_comment_literals(self):
        page = '<html><head><script>const x="</head>";</script></head><body><script>const x="</body>";</script><!-- </body> --></body></html>'
        result = insert_before_closing_tag(page, 'body', '<template>license</template>')
        self.assertIn('const x="</body>";', result)
        self.assertTrue(result.endswith('<template>license</template></body></html>'))
        self.assertEqual(insert_before_closing_tag('<BODY>x</BODY>', 'body', 'tail'), '<BODY>xtail</BODY>')
        for separator in ('\u2028', '\u2029', '\r', '\v', '\f', '\x85'):
            prefix = '<html><body>hello' + separator + 'world\n'
            self.assertEqual(insert_before_closing_tag(prefix + '</body></html>', 'body', 'tail'),
                             prefix + 'tail</body></html>')
        with self.assertRaises(ValueError):
            insert_before_closing_tag('<script>const x="</body>"</script>', 'body', 'tail')


if __name__ == '__main__':
    unittest.main()
