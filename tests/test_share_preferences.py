"""Editing survives refresh without mixing years/accounts or retaining deleted text."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'reading-yearbook-skill/scripts'))
from build_reading_html import adapt_data, build_html
from generate_reading_html import deliver
from test_reading_html_delivery import snapshot


class SharePreferenceTests(unittest.TestCase):
    def test_scope_is_opaque_and_round_trips_without_credential(self):
        raw = {'year':2026, 'books':[], 'summary':{}}
        a, b = adapt_data(raw), adapt_data(raw)
        self.assertRegex(a['edit_scope'], r'^[a-f0-9]{32}$')
        self.assertNotEqual(a['edit_scope'], b['edit_scope'])
        self.assertEqual(adapt_data(a)['edit_scope'], a['edit_scope'])
        self.assertNotEqual(adapt_data({**raw,'edit_scope':'malformed'})['edit_scope'], 'malformed')

    def test_delivery_reuses_same_year_scope_and_reports_materials(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state = root/'latest.json'
            deliver(snapshot(0), {'year':2026,'books':[]}, {}, root/'index.html', state_path=state)
            previous = json.loads(state.read_text('utf-8'))
            result = deliver(snapshot(0), {'year':2026,'books':[]}, {}, root/'index.html', previous, state)
            self.assertEqual(json.loads(state.read_text('utf-8'))['edit_scope'], previous['edit_scope'])
            self.assertEqual(result['materials'], {'books':0,'with_highlights':0,'with_thoughts':0,'without_loaded_notes':0,'verified_empty_notes':0,'incomplete_notes':0})
            previous['year'] = 2025
            deliver(snapshot(0), {'year':2026,'books':[]}, {}, root/'index.html', previous, state)
            self.assertNotEqual(json.loads(state.read_text('utf-8'))['edit_scope'], previous['edit_scope'])
            missing = deliver(snapshot(),{'year':2026,'books':[]},{},root/'missing.html')['materials']
            self.assertEqual(missing['without_loaded_notes'],1)
            self.assertEqual(missing['verified_empty_notes'],0)
            self.assertEqual(missing['incomplete_notes'],1)
            unsupported = {'year':2026,'books':[{'book_id':'one','collection':{'highlights':'unsupported','thoughts':'unsupported'},'highlights':[],'thoughts':[]}]}
            self.assertEqual(deliver(snapshot(),unsupported,{},root/'unsupported.html')['materials']['verified_empty_notes'],0)

    @unittest.skipUnless(os.environ.get('SHARE_NODE') and os.environ.get('SHARE_PLAYWRIGHT'), 'browser runtime not configured')
    def test_browser_editing_and_update_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = {'year':2026,'edit_scope':'a'*32,'source_mode':'sample','summary':{'book_count':2},'books':[
                {'book_id':'one','title':'选择测试','author':'甲','highlights':[
                    {'source_id':'fragment','text':'因此这样。'},
                    {'source_id':'complete','text':'先把知道的事实写下来，再看看还有多少判断只是自己的猜测，然后留下一点思考的余地。'}],
                 'thoughts':[{'source_id':'personal','text':'这是我的真实想法，没有改写的个人笔记。'}]},
                {'book_id':'two','title':'无笔记的书','author':'乙'}]}
            def write(name, raw):
                build_html(adapt_data(raw),root/(name+'.html'))
            write('initial',source)
            updated = json.loads(json.dumps(source))
            updated['books'][0]['thoughts'].insert(0,{'source_id':'new-note','text':'新增笔记并不改变原有选择。'})
            updated['books'].append({'book_id':'three','title':'新增一本','author':'丙'})
            updated['summary']['book_count']=3
            write('updated',updated)
            changed = json.loads(json.dumps(updated))
            changed['books'][0]['thoughts'][1]['text']='来源ID相同，但是原文已变更。'
            write('changed',changed)
            write('other',{**source,'edit_scope':'b'*32})
            write('year',{**source,'year':2025})
            write('removed',{**source,'books':[source['books'][1]],'summary':{'book_count':1}})
            env={**os.environ,'NODE_PATH':str(Path(os.environ['SHARE_PLAYWRIGHT']).parent),
                 'BROWSER_EXECUTABLE':os.environ.get('SHARE_BROWSER','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')}
            result=subprocess.run([os.environ['SHARE_NODE'],str(ROOT/'tests/reading_share_preferences.cjs'),str(root)],env=env,capture_output=True,text=True,encoding='utf-8',timeout=120)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
