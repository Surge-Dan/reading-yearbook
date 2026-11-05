import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reading-yearbook-skill/scripts'))

class PortraitTests(unittest.TestCase):
    def engine(self):
        try:import reading_portrait;return reading_portrait
        except ImportError:self.fail('reading portrait missing')
    def test_missing_evidence_is_unknown_not_fifty_percent(self):
        p=self.engine().profile([],[],2026)
        self.assertEqual(p['annual']['type'],'倾向未明')
        self.assertTrue(all(a['left_percent'] is None for a in p['annual']['axes']))
    def test_only_dated_own_thoughts_are_valid_evidence(self):
        books=[{'book_id':'a','thoughts':[{'source_id':'x','created_at':'2026-01-02','text':'自己的想法'}],'highlights':[]}]
        with self.assertRaises(ValueError):self.engine().profile([{'source_id':'unknown','axis':'EI','side':'I','reason':'依据'}],books,2026)
    def test_sufficient_distinct_evidence_and_month_filter(self):
        books=[{'book_id':str(i),'thoughts':[{'source_id':str(i),'created_at':'2026-01-02','text':'个人想法'}]} for i in range(3)]
        signals=[{'source_id':str(i),'axis':'EI','side':'I' if i<2 else 'E','reason':'表达指向'} for i in range(3)]
        p=self.engine().profile(signals,books,2026)
        self.assertEqual(p['annual']['axes'][0]['left_percent'],33)
        self.assertIsNone(p['months']['2026-02']['axes'][0]['left_percent'])
        with self.assertRaises(ValueError):self.engine().profile(signals+[signals[0]],books,2026)
        for side in ('','EI',None,[]):
            with self.subTest(side=side),self.assertRaises(ValueError):self.engine().profile([{**signals[0],'side':side}],books,2026)
