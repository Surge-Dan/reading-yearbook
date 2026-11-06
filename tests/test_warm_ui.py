import json,sys,tempfile,unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'reading-yearbook-skill/scripts'))
from build_reading_html import adapt_data,build_html
from report_reader import reader_page
from test_report_reader import bundle

class WarmUITests(unittest.TestCase):
    def test_standalone_reader_controls_share_report_theme(self):
        with tempfile.TemporaryDirectory() as tmp,sync_playwright() as p:
            target=Path(tmp)/'reader.html'
            package=bundle(sample=True)
            target.write_text(reader_page({'analysis':package['analysis'],'digest':package['digest']}),'utf-8')
            browser=p.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless=True)
            try:
                page=browser.new_page(reduced_motion='reduce')
                page.goto(target.as_uri(),wait_until='networkidle')
                page.locator('#ebookShareToggle').click()
                self.assertEqual(page.locator('#ebookExportZip').evaluate('el=>getComputedStyle(el).backgroundColor'),'rgb(184, 50, 37)')
                self.assertEqual(page.locator('#ebookRatio').evaluate('el=>getComputedStyle(el).borderRadius'),'10px')
                self.assertEqual(page.locator('#ebookRatio').evaluate('el=>getComputedStyle(el).backgroundColor'),'rgb(255, 253, 246)')
                self.assertEqual(page.locator('#ebookDownloadMd').evaluate('el=>getComputedStyle(el).color'),'rgb(32, 90, 197)')
                page.set_viewport_size({'width':375,'height':950})
                self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
            finally:browser.close()

    def test_report_dialog_selects_focus_and_mobile_share_one_theme(self):
        with tempfile.TemporaryDirectory() as tmp,sync_playwright() as p:
            data=adapt_data(json.loads((ROOT/'reading-yearbook-skill/examples/reading-html-demo/demo-data.json').read_text('utf-8')))
            for book in data['books']:
                book['highlights']=[{'text':'用于验证滚动的划线。','created_at':'2026-01-01'}]*40
            target=Path(tmp)/'report.html';build_html(data,target)
            browser=p.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless=True)
            try:
                page=browser.new_page(viewport={'width':1440,'height':950},reduced_motion='reduce')
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(target.as_uri(),wait_until='networkidle')
                color=lambda selector:page.locator(selector).evaluate('(el)=>getComputedStyle(el).backgroundColor')
                self.assertEqual(color('.paper'),'rgb(255, 253, 246)')
                book=page.locator('.book').first
                book.scroll_into_view_if_needed()
                original_hash=page.evaluate('location.hash')
                book.click()
                self.assertTrue(page.locator('#detail').evaluate('(el)=>el.open'))
                self.assertEqual(color('#detail'),'rgb(255, 253, 246)')
                detail=page.locator('#detail')
                close=detail.get_by_role('button',name='关闭书籍详情')
                initial_y=close.bounding_box()['y']
                detail.evaluate('el=>el.scrollTop=el.scrollHeight')
                self.assertGreater(detail.evaluate('el=>el.scrollTop'),500)
                self.assertAlmostEqual(close.bounding_box()['y'],initial_y,delta=1)
                close.click()
                page.wait_for_function('hash=>location.hash===hash',arg=original_hash)
                book.click()
                detail.locator('.detail-identity h2').click()
                self.assertTrue(detail.evaluate('el=>el.open'))
                page.mouse.click(5,5)
                page.wait_for_function('hash=>location.hash===hash',arg=original_hash)
                self.assertFalse(detail.evaluate('el=>el.open'))
                book.click()
                page.keyboard.press('Escape')
                page.locator('.rhythm-chart .chart-table summary').click()
                page.locator('#openSources').click()
                self.assertEqual(color('#sourcesDialog'),'rgb(255, 253, 246)')
                page.keyboard.press('Escape')
                ratio=page.get_by_role('button',name='1:1',exact=True)
                ratio.click()
                self.assertEqual(page.locator('#ratio').input_value(),'1:1')
                page.keyboard.press('Tab')
                ratio.focus()
                self.assertNotEqual(ratio.evaluate('el=>getComputedStyle(el).outlineStyle'),'none')
                self.assertEqual(page.locator('#readingPortrait select').count(),0)
                for width in (768,375):
                    page.set_viewport_size({'width':width,'height':950})
                    self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
                self.assertEqual(errors,[])
            finally:browser.close()
