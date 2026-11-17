import sys,tempfile,unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reading-yearbook-skill/scripts'))
from build_reading_html import adapt_data,build_html

class MonthlyAxisTests(unittest.TestCase):
    def test_scales_and_all_month_labels_adapt_to_source(self):
        with tempfile.TemporaryDirectory() as tmp,sync_playwright() as p:
            target=Path(tmp)/'report.html'
            build_html(adapt_data({'year':2025,'as_of':'2026-01-01','books':[],
                'summary':{'monthly_read_seconds':[i*3600 for i in range(1,13)]}}),target)
            browser=p.chromium.launch(channel='msedge',headless=True)
            try:
                page=browser.new_page(reduced_motion='reduce');page.goto(target.as_uri(),wait_until='networkidle')
                results=page.evaluate('''async()=>{
                    const data=JSON.parse(document.querySelector('#reading-data').textContent),art=JSON.parse(document.querySelector('#reading-art').textContent);
                    const cases=[[],[0,0],[60,120],[3600,7200],[300*3600,600*3600],[null,0,60],Array(12).fill(null)];
                    const scales=cases.map(v=>ReadingShareArtwork.monthlyScale(v));
                    const renderer=ReadingShareArtwork.create({data,art,loadImage:src=>new Promise((res,rej)=>{const im=new Image();im.onload=()=>res(im);im.onerror=rej;im.src=src})});
                    const charts=[];for(const ratio of ['1:1','3:4','4:5'])for(const kind of ['cover','stats'])charts.push((await renderer.render({id:kind,kind},ratio)).readingLayout);
                    return {scales,charts};
                }''')
                scales=results['scales']
                self.assertGreater(scales[2]['top'],0)
                self.assertLess(scales[2]['top'],1)
                self.assertGreaterEqual(scales[4]['top'],600)
                self.assertEqual(scales[0]['top'],scales[1]['top'])
                for scale in scales:
                    self.assertGreater(scale['top'],0)
                    self.assertEqual(scale['ticks'][0],0)
                    self.assertEqual(scale['ticks'][-1],scale['top'])
                for chart in results['charts']:
                    labels=[t['text'] for t in chart['text']]
                    for month in range(1,13):self.assertIn(str(month)+('月' if chart['page']=='cover' else ''),labels)
                    if chart['page']=='cover':self.assertEqual(len(next(c for c in chart['charts'] if c['kind']=='calendar')['cells']),365)
                    for t in chart['text']:
                        self.assertGreaterEqual(t['x'],20)
                        self.assertLessEqual(t['x']+t['w'],880)
                        self.assertLessEqual(t['y']+t['h'],chart['height']-20)
                dense=page.evaluate('''async()=>{
                    const data=JSON.parse(document.querySelector('#reading-data').textContent),art=JSON.parse(document.querySelector('#reading-art').textContent);
                    data.books=Array.from({length:250},(_,i)=>({book_id:String(i),title:'测试书'+i,author:'作者',category:'分类'+i%25,highlights:[],thoughts:[]}));
                    const r=ReadingShareArtwork.create({data,art,loadImage:()=>Promise.reject(Error('missing'))}),out=[];
                    for(const ratio of ['1:1','3:4','4:5'])out.push((await r.render({id:'distribution',kind:'distribution'},ratio)).readingLayout);
                    return out;
                }''')
                for chart in dense:
                    self.assertEqual(sum(c['count'] for c in chart['charts'] if c['kind']=='category'),250)
                    texts=chart['text']
                    for i,a in enumerate(texts):
                        for b in texts[i+1:]:
                            dx=min(a['x']+a['w'],b['x']+b['w'])-max(a['x'],b['x'])
                            dy=min(a['y']+a['h'],b['y']+b['h'])-max(a['y'],b['y'])
                            self.assertFalse(dx>2 and dy>2,(a['text'],b['text']))
            finally:browser.close()

