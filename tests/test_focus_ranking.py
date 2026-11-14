import sys,tempfile,unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reading-yearbook-skill/scripts'))
from build_reading_html import adapt_data,build_html

class FocusRankingTests(unittest.TestCase):
    def test_ranking_scope_ties_expansion_and_export(self):
        books=[{'book_id':str(i),'title':'测试书'+str(i),'annual_reading_seconds':v} for i,v in enumerate([3600,3600,1800,1200,600,0,None])]
        books += [{'book_id':'private','title':'私密标记','secret':True,'annual_reading_seconds':9000},
                  {'book_id':'audio','title':'有声标记','kind':'audio','annual_reading_seconds':7200}]
        with tempfile.TemporaryDirectory() as tmp,sync_playwright() as p:
            path=Path(tmp)/'index.html';build_html(adapt_data({'year':2025,'books':books}),path)
            browser=p.chromium.launch(channel='msedge',headless=True)
            try:
                page=browser.new_page(accept_downloads=True,reduced_motion='reduce')
                page.goto(path.as_uri(),wait_until='networkidle')
                result=page.evaluate('ReadingShareArtwork.focusRanking(JSON.parse(document.querySelector("#reading-data").textContent).books)')
                self.assertEqual([r['focus_rank'] for r in result['rows']],[1,1,3,4,5,None])
                self.assertEqual(result['total'],10800)
                self.assertAlmostEqual(result['topShare'],9000/10800)
                self.assertEqual(page.locator('#investment .investment-row:visible').count(),5)
                page.locator('#expandFocus').click()
                self.assertEqual(page.locator('#investment .investment-row:visible').count(),6)
                self.assertIn('并列投入最多',page.locator('#focusSummary').inner_text())
                self.assertNotIn('有声标记',page.locator('#investment').inner_text())
                page.locator('#audioFocus summary').click()
                self.assertIn('有声标记',page.locator('#audioFocus').inner_text())
                for ratio in ('1:1','3:4','4:5'):
                    rows=page.evaluate('''async ratio=>{
                        const data=JSON.parse(document.querySelector('#reading-data').textContent),art=JSON.parse(document.querySelector('#reading-art').textContent);
                        const cv=await ReadingShareArtwork.create({data,art,loadImage:()=>Promise.reject(Error('missing'))}).render({id:'focus',kind:'focus'},ratio);
                        return cv.readingLayout;
                    }''',ratio)
                    self.assertTrue(any(t['text']=='2025' for t in rows['text']))
                    for t in rows['text']:
                        self.assertLessEqual(t['y']+t['h'],rows['height']-20)
                    self.assertFalse(any('私密标记' in t['text'] or '有声标记' in t['text'] for t in rows['text']))
                    for i,a in enumerate(rows['text']):
                        for b in rows['text'][i+1:]:
                            dx=min(a['x']+a['w'],b['x']+b['w'])-max(a['x'],b['x'])
                            dy=min(a['y']+a['h'],b['y']+b['h'])-max(a['y'],b['y'])
                            self.assertFalse(dx>2 and dy>2,(a['text'],b['text']))
                edge=page.evaluate('''()=>{
                    const f=ReadingShareArtwork.focusRanking;
                    return [f([]),f([{book_id:'a',reading_seconds:0}]),f([{book_id:'a',reading_seconds:100},{book_id:'a',reading_seconds:100},{book_id:'bad',reading_seconds:NaN},{book_id:'negative',reading_seconds:-1}])];
                }''')
                self.assertEqual(edge[0]['total'],0)
                self.assertIsNone(edge[1]['topShare'])
                self.assertEqual(len(edge[2]['rows']),1)
                with page.expect_download() as event:page.locator('#exportFocus').click()
                self.assertEqual(event.value.suggested_filename,'2025-focus-ranking.png')
            finally:browser.close()
