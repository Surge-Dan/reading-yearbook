import sys,unittest
import copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reading-yearbook-skill/scripts'))

class PortraitTests(unittest.TestCase):
    def engine(self):
        try:import reading_portrait;return reading_portrait
        except ImportError:self.fail('reading portrait missing')

    def fixture(self):
        return {'year':2026,'books':[
            {'book_id':'a','title':'A','category':'essay','thoughts':[{'source_id':'t','created_at':'2026-01-01','text':'my reflection'}]},
            {'book_id':'b','title':'B','category':'essay','highlights':[{'source_id':str(i),'created_at':'2026-01-02','text':'passage '+str(i)} for i in range(3)]}]}

    def annotation(self,data):
        return {'year':2026,'material_fingerprint':self.engine().material_fingerprint(data),'signals':[
            {'source_id':sid,'source_kind':kind,'axis':'EI','side':'I','reason':'independent reflection'}
            for sid,kind in [('t','thought'),('0','highlight'),('1','highlight')]]}

    def test_pending_is_distinct_from_insufficient(self):
        e=self.engine();d=self.fixture()
        self.assertEqual(e.analysis_state(d)['status'],'pending')
        self.assertIn('尚待分析',e.section(d))
        self.assertNotIn('现有记录不足',e.section(d))
        d['books'][0]['thoughts']=[]
        self.assertEqual(e.analysis_state(d)['status'],'limited')
        self.assertNotIn('portrait-axis',e.section(d))

    def test_apply_reuse_and_changed_material(self):
        e=self.engine();d=self.fixture();payload=self.annotation(d)
        ready=e.apply_analysis(d,payload)
        self.assertEqual(e.analysis_state(e.reuse_analysis(d,ready))['status'],'ready')
        changed=copy.deepcopy(d);changed['books'][0]['thoughts'][0]['text']='updated'
        self.assertEqual(e.analysis_state(e.reuse_analysis(changed,ready))['status'],'pending')
        with self.assertRaises(ValueError):e.apply_analysis(changed,payload)

    def test_private_sources_excluded_and_rejected(self):
        e=self.engine();d=self.fixture();fingerprint=e.material_fingerprint(d)
        d['books'].append({'book_id':'private','secret':True,'thoughts':[{'source_id':'private','created_at':'2026-01-01','text':'private record'}]})
        self.assertEqual(e.material_fingerprint(d),fingerprint)
        self.assertNotIn('private record',str(e.prepare_packet(d)))
        payload=self.annotation(d);payload['signals'][0]['source_id']='private'
        with self.assertRaises(ValueError):e.apply_analysis(d,payload)

    def test_packet_is_bounded_and_distinct(self):
        packet=self.engine().prepare_packet(self.fixture(),3)['selected_records']
        self.assertEqual(len(packet),3)
        self.assertEqual(packet[0]['source_kind'],'thought')
        self.assertEqual(len({(r['source_kind'],r['source_id']) for r in packet}),3)
    def test_missing_evidence_is_unknown_not_fifty_percent(self):
        p=self.engine().profile([],[],2026)
        self.assertEqual(p['annual']['type'],'倾向未明')
        self.assertTrue(all(a['left_percent'] is None for a in p['annual']['axes']))
    def test_only_dated_own_thoughts_are_valid_evidence(self):
        books=[{'book_id':'a','thoughts':[{'source_id':'x','created_at':'2026-01-02','text':'自己的想法'}],'highlights':[]}]
        with self.assertRaises(ValueError):self.engine().profile([{'source_id':'unknown','axis':'EI','side':'I','reason':'依据'}],books,2026)
    def test_highlights_support_but_do_not_outweigh_personal_thoughts(self):
        def note(sid):
            return {'source_id':sid,'created_at':'2026-01-02','text':'阅读记录'}
        books=[{'book_id':'a','thoughts':[note('t')]},
               {'book_id':'b','highlights':[note('h1'),note('h2')]}]
        signals=[{'source_id':sid,'axis':'EI','side':side,'reason':'依据','source_kind':kind}
                 for sid,side,kind in [('t','I','thought'),('h1','E','highlight'),('h2','E','highlight')]]
        engine=self.engine()
        axis=engine.profile(signals,books,2026)['annual']['axes'][0]
        self.assertEqual(axis['left_percent'],33)
        self.assertEqual(axis['evidence'][1]['source_kind'],'highlight')
        self.assertIsNone(engine.profile(signals[1:],books,2026)['annual']['axes'][0]['left_percent'])

    def test_section_only_renders_annual_portrait(self):
        page=self.engine().section({'year':2026,'books':[]})
        self.assertIn('全年阅读侧写',page)
        self.assertNotIn('portraitMonth',page)
        self.assertNotIn('倾向未明',page)
    def test_sufficient_distinct_evidence_and_month_filter(self):
        books=[{'book_id':str(i),'thoughts':[{'source_id':str(i),'created_at':'2026-01-02','text':'个人想法'}]} for i in range(3)]
        signals=[{'source_id':str(i),'axis':'EI','side':'I' if i<2 else 'E','reason':'表达指向'} for i in range(3)]
        p=self.engine().profile(signals,books,2026)
        self.assertEqual(p['annual']['axes'][0]['left_percent'],33)
        self.assertIsNone(p['months']['2026-02']['axes'][0]['left_percent'])
        with self.assertRaises(ValueError):self.engine().profile(signals+[signals[0]],books,2026)
        for side in ('','EI',None,[]):
            with self.subTest(side=side),self.assertRaises(ValueError):self.engine().profile([{**signals[0],'side':side}],books,2026)

