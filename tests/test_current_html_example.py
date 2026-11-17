"""Public examples must remain aligned with the shipped renderer, not a stale deck."""
import json
import base64
import io
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'reading-yearbook-skill'
DEMO = ROOT / 'examples/reading-html-demo'


class CurrentExampleTests(unittest.TestCase):
    maxDiff = 500
    def test_public_example_uses_current_css_and_inline_scripts(self):
        page = (DEMO / 'index.html').read_text('utf-8')
        sys.path.insert(0, str(ROOT / 'scripts'))
        from embed_fonts import font_css
        embedded=json.loads(re.search(r'<script id="reading-data" type="application/json">(.*?)</script>',page,re.S).group(1))
        expected_css = '\n'.join((ROOT / 'assets' / name).read_text('utf-8')
                                 for name in ('reading-app.css', 'reading-art.css', 'ebook-app.css', 'reading-refinement.css'))
        expected_css += '\n' + font_css(embedded)
        actual_css=re.search(r'<style>(.*?)</style>', page, re.S).group(1).strip()
        # WOFF2 compression varies across supported fontTools versions. Compare
        # exact CSS plus decoded glyph geometry/metrics, not encoder bytes.
        font_url=r'data:font/[^;]+;base64,([A-Za-z0-9+/=]+)'
        self.assertEqual(re.sub(font_url, 'EMBEDDED_FONT', actual_css),
                         re.sub(font_url, 'EMBEDDED_FONT', expected_css.strip()))
        actual_fonts=re.findall(font_url, actual_css);expected_fonts=re.findall(font_url, expected_css)
        self.assertEqual(len(actual_fonts), 2)
        from fontTools.ttLib import TTFont
        for actual_binary,expected_binary in zip(actual_fonts,expected_fonts):
            with TTFont(io.BytesIO(base64.b64decode(actual_binary))) as actual, TTFont(io.BytesIO(base64.b64decode(expected_binary))) as expected:
                a_map=actual.getBestCmap();e_map=expected.getBestCmap()
                self.assertEqual(set(a_map), set(e_map))
                self.assertEqual(actual['head'].unitsPerEm, expected['head'].unitsPerEm)
                for char,a_name in a_map.items():
                    e_name=e_map[char]
                    self.assertEqual(actual['hmtx'][a_name], expected['hmtx'][e_name])
                    self.assertEqual(actual['glyf'][a_name].getCoordinates(actual['glyf']),
                                     expected['glyf'][e_name].getCoordinates(expected['glyf']))
        for script_id,asset in [('reading-share-mounted','reading-share-art.js'),('ebook-app-mounted','ebook-app.js')]:
            self.assertEqual(re.search(r'<script id="'+script_id+r'">(.*?)</script>',page,re.S).group(1).strip(),(ROOT/'assets'/asset).read_text('utf-8').strip())
        expected_app='\n'.join((ROOT/'assets'/name).read_text('utf-8') for name in ('reading-share-state.js','reading-app.js'))
        self.assertEqual(re.search(r'<script>(.*?)</script>',page,re.S).group(1).strip(),expected_app.strip())
        self.assertIn('data-reader-mode="readonly"',page)
        self.assertNotIn('id="ebookUpload"',page)
        embedded=json.loads(re.search(r'<script id="reading-data" type="application/json">(.*?)</script>',page,re.S).group(1))
        self.assertEqual(embedded['distillations'][0]['source_mode'],'sample')
        sample = json.loads((DEMO / 'demo-data.json').read_text('utf-8'))
        self.assertTrue(sample['features']['daily'])
        self.assertEqual(embedded['features']['daily'], sample['features']['daily'])

    def test_demo_materials_are_fictional_and_statistics_agree(self):
        data = json.loads((DEMO / 'demo-data.json').read_text('utf-8'))
        self.assertEqual(data['source_mode'], 'sample')
        self.assertEqual(data['verification_status'], 'sample_verified')
        self.assertEqual(data['summary']['book_count'], len(data['books']))
        self.assertEqual(data['summary']['total_read_seconds'], sum(data['summary']['monthly_read_seconds']))
        self.assertEqual(data['summary']['total_read_seconds'], sum(b['annual_reading_seconds'] for b in data['books']))
        self.assertEqual(data['summary']['note_count'], sum(len(b['highlights'])+len(b['thoughts']) for b in data['books']))
        self.assertEqual({(bool(b['highlights']), bool(b['thoughts'])) for b in data['books']},
                         {(True, True), (True, False), (False, True), (False, False)})

    def test_export_artifacts_cover_all_pages_with_correct_dimensions(self):
        from PIL import Image
        report = json.loads((DEMO / 'preview-manifest.json').read_text('utf-8'))
        data = json.loads((DEMO / 'demo-data.json').read_text('utf-8'))
        self.assertEqual(report['pages'], len(data['books']) + 4)
        self.assertEqual(report['pages'], len(report['images']))
        self.assertTrue(report['sample_data'])
        self.assertTrue(report['browser_png_matches_preview'])
        self.assertLessEqual(report['max_premultiplied_channel_delta'], 1)
        for row in report['images']:
            with self.subTest(page=row['filename']):
                with Image.open(DEMO / 'images' / row['filename']) as image:
                    image.load()
                    self.assertEqual(image.size, (900, 1200))


if __name__ == '__main__':
    unittest.main()
