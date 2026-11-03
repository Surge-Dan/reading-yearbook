"""Actual offline browser checks for optional notes and the compact reader."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reading-yearbook-skill/scripts'))
from build_reading_html import adapt_data,build_html
from ebook_document import parse_document
from ebook_light import distill
from distillation_result import make_bundle
from test_ebook_light import LightRunner


class OptionalReaderBrowserTests(unittest.TestCase):
    def test_no_distillation_report_exports_and_compact_note_reader(self):
        with tempfile.TemporaryDirectory() as tmp,sync_playwright() as p:
            root=Path(tmp); source=root/'受控短篇.txt'
            source.write_text('先把条件弄清楚，再比较不同选择。','utf-8')
            analysis=distill(source,root/'book',LightRunner())
            document=parse_document(source);document['source_mode']='sample'
            package=make_bundle(analysis,document,(root/'book/DIGEST.md').read_text('utf-8'))
            browser=p.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless=True)
            try:
                for attached in (False,True):
                    data=adapt_data({'year':2026,'source_mode':'sample','summary':{'book_count':0},'books':[]})
                    if attached:data['distillations']=[package]
                    target=root/('with.html' if attached else 'without.html');build_html(data,target)
                    context=browser.new_context(accept_downloads=True,reduced_motion='reduce')
                    context.set_offline(True); page=context.new_page(); errors=[];requests=[]
                    page.on('pageerror',lambda e:errors.append(str(e)))
                    page.on('request',lambda r:requests.append(r.url) if r.url.startswith(('http:','https:')) else None)
                    page.goto(target.as_uri(),wait_until='networkidle')
                    page.evaluate('document.fonts.ready')
                    for width in (1440,375):
                        page.set_viewport_size({'width':width,'height':950})
                        self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
                    page.set_viewport_size({'width':1440,'height':950})
                    self.assertEqual(page.locator('#ebook').is_visible(),attached)
                    self.assertEqual(page.locator('a[href="#ebook"]').first.is_visible(),attached)
                    self.assertEqual(page.locator('input[type="file"]').count(),0)
                    with page.expect_download() as event:page.locator('#exportJson').click()
                    export=root/('attached.json' if attached else 'plain.json');event.value.save_as(export)
                    self.assertEqual(len(json.loads(export.read_text('utf-8')).get('distillations',[])),int(attached))
                    with page.expect_download() as event:page.locator('#exportOne').click()
                    png=root/'annual.png';event.value.save_as(png)
                    with Image.open(png) as image:self.assertEqual(image.size,(900,1200))
                    if attached:
                        headings=page.locator('#ebookResult > section > h3').all_text_contents()
                        self.assertEqual(headings,['这本书讲什么','最值得记住的东西','读完想带走的东西','读后余味','参考资料'])
                        page.evaluate("Object.defineProperty(navigator,'clipboard',{value:{writeText:async text=>window.copied=text}})")
                        page.locator('#ebookCopyAll').click()
                        copied=page.evaluate('window.copied')
                        self.assertTrue(copied.startswith(package['digest']))
                        self.assertIn('功能测试示例',copied)
                        with page.expect_download() as event:page.locator('#ebookDownloadMd').click()
                        md=root/'digest.md';event.value.save_as(md)
                        self.assertEqual(md.read_text('utf-8'),copied)
                        page.locator('#ebookShareToggle').click()
                        with page.expect_download() as event:page.locator('#ebookExportPng').click()
                        png=root/'digest.png';event.value.save_as(png)
                        with Image.open(png) as image:self.assertEqual(image.size,(900,1200))
                    self.assertEqual(errors,[]);self.assertEqual(requests,[])
                    context.close()
            finally:browser.close()


if __name__=='__main__':unittest.main()
