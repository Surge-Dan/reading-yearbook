"""Exports work with no installed Noto fonts, or a failed FontFaceSet.load."""
import sys
import tempfile
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'reading-yearbook-skill/scripts'))
from build_reading_html import adapt_data, build_html


class FontPortabilityTests(unittest.TestCase):
    def test_embedded_fallback_and_failed_font_loading_do_not_disable_exports(self):
        with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
            target = Path(tmp)/'report.html'
            build_html(adapt_data({'year': 2026, 'source_mode': 'sample', 'books': [], 'summary': {'book_count': 0}}), target)
            html = target.read_text('utf8')
            self.assertIn('url(data:font/', html)
            html = html.replace('Noto Serif SC', 'Absent Serif Test Font').replace('Noto Sans SC', 'Absent Sans Test Font')
            target.write_text(html, 'utf8')
            browser = p.chromium.launch(channel='msedge', headless=True)
            try:
                for fail_load in (False, True):
                    context = browser.new_context(offline=True)
                    if fail_load:
                        context.add_init_script("FontFaceSet.prototype.load=()=>Promise.reject(Error('font unavailable'))")
                    page = context.new_page();errors=[]
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.goto(target.as_uri(), wait_until='networkidle')
                    page.wait_for_function("!document.querySelector('#exportOne').disabled")
                    if not fail_load:
                        self.assertTrue(page.evaluate("document.fonts.check('400 28px ReadingSans')"))
                    with page.expect_download() as event:
                        page.locator('#exportOne').click()
                    self.assertTrue(event.value.suggested_filename.endswith('.png'))
                    self.assertEqual(errors, [])
                    context.close()
            finally:
                browser.close()


if __name__ == '__main__':
    unittest.main()
