"""Controlled text fixtures; no live-model quality or speed claim."""
import importlib
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reading-yearbook-skill/scripts'))


class LightRunner:
    def __init__(self, fail=False, bad_quote=False, long=False, mode='current-agent-instructed-tools'):
        self.calls=[]; self.fail=fail; self.bad_quote=bad_quote; self.long=long; self.mode=mode
    def info(self): return {'name':'controlled-light','available':True,'mode':self.mode}
    def generate(self,prompt,**kwargs):
        stage=prompt.split('STAGE:',1)[1].split('\n',1)[0]
        payload=json.loads(prompt.split('SOURCE_DATA_JSON:\n',1)[1]); self.calls.append((stage,payload))
        if stage=='title-identify':
            from test_book_title import candidate
            return {'status':'identified','candidates':[candidate()],'searches_used':1}
        if stage=='title-research':
            from test_book_title import evidence
            return evidence()
        if stage=='light-read':
            elements=payload['chunk']['elements']
            return {'notes':[{'title':'先把条件弄清楚','explanation':'先询问，再判断。',
                'sources':[{'element_id':e['element_id'],'location':e['location'],'quote':e['text'][:20]}]}
                for e in (elements[:1] if len(elements)==1 else [elements[0],elements[-1]])]}
        if stage=='light-compose':
            if self.fail: self.fail=False; raise ValueError('controlled interrupted synthesis')
            e=payload['elements'][0]
            source={'element_id':e['element_id'],'location':e['location'],'quote':e['text'][:20]}
            if self.bad_quote: source['quote']='伪造的原文引语'
            return {'overview':'从一个具体的问题出发，先听清楚对方，再决定如何回应。',
                'themes':[{'title':'先理解，再回应','explanation':'先问清对方的意思。例如遇到分歧，不急着替对方解释。'+('字'*3000 if self.long else ''),'sources':[source]}],
                'insights':[{'title':'下一次争执前先停一停','explanation':'先复述对方的意思，再询问理解得是否准确。','sources':[source]}],
                'memorable_passages':[],
                'review':{'status':'ready','reason':'','paragraphs':[{'text':'我喜欢这里留给理解的一点耐心。一个停顿，有时比一句漂亮的话更有用。','sources':[source],'quotes':[]}]}}
        raise AssertionError(stage)


class LightTests(unittest.TestCase):
    def engine(self):
        try: return importlib.import_module('ebook_light')
        except ModuleNotFoundError: self.fail('缺少已确认的轻量蒸馏引擎')

    def source(self,root):
        path=Path(root)/'书.txt'; path.write_text('先把条件弄清楚，再比较不同选择。',encoding='utf-8'); return path

    def test_short_book_uses_read_and_compose_only_and_has_compact_bundle(self):
        engine=self.engine()
        from distillation_result import load_bundle
        with tempfile.TemporaryDirectory() as tmp:
            runner=LightRunner(); out=Path(tmp)/'out'
            a=engine.distill(self.source(tmp),out,runner)
            self.assertEqual([s for s,_ in runner.calls],['light-read','light-compose'])
            self.assertEqual(a['methods'],[])
            self.assertEqual(a['review']['status'],'ready')
            self.assertEqual(load_bundle(out/'distillation.json')['analysis'],a)
            self.assertFalse((out/'methods').exists())
            self.assertLess(len((out/'DIGEST.md').read_text('utf-8')),4000)

    def test_cached_reading_survives_failed_compose(self):
        engine=self.engine()
        with tempfile.TemporaryDirectory() as tmp:
            runner=LightRunner(fail=True); path=self.source(tmp); out=Path(tmp)/'out'
            with self.assertRaisesRegex(ValueError,'controlled'): engine.distill(path,out,runner)
            self.assertFalse((out/'distillation.json').exists())
            engine.distill(path,out,runner)
            self.assertEqual([s for s,_ in runner.calls],['light-read','light-compose','light-compose'])
            count=len(runner.calls); engine.distill(path,out,runner)
            self.assertEqual(count,len(runner.calls))

    def test_every_chunk_including_last_chapter_is_read_once(self):
        engine=self.engine()
        from ebook_document import parse_document
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'long.md';path.write_text('# 开头\n'+('甲乙'*26000)+'\n# 末章\n最后的证据。','utf-8')
            runner=LightRunner(); result=engine.distill(path,Path(tmp)/'out',runner)
            read=[payload for stage,payload in runner.calls if stage=='light-read']
            actual=''.join(e['text'] for row in read for e in row['chunk']['elements'])
            expected=''.join(e['text'] for e in parse_document(path)['elements'])
            self.assertEqual(actual,expected)
            self.assertIn('最后的证据',actual)
            self.assertEqual(len(runner.calls),len(read)+1)
            self.assertTrue(result['coverage']['complete'])

    def test_first_half_quote_survives_coalesced_long_element(self):
        engine=self.engine()
        class FirstHalfRunner(LightRunner):
            def generate(self,prompt,**kwargs):
                result=super().generate(prompt,**kwargs)
                if 'STAGE:light-read\n' in prompt: result['notes']=result['notes'][:1]
                return result
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'halves.txt';path.write_text('甲'*12000+'乙'*12000,'utf-8')
            a=engine.distill(path,Path(tmp)/'out',FirstHalfRunner())
            self.assertEqual(a['themes'][0]['sources'][0]['quote'],'甲'*20)

    def test_compose_never_receives_entire_long_source_element(self):
        engine=self.engine()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'long.txt';path.write_text('甲'*45000+'乙'*45000,'utf-8')
            runner=LightRunner();engine.distill(path,Path(tmp)/'out',runner)
            payload=[value for stage,value in runner.calls if stage=='light-compose'][0]
            self.assertLess(sum(len(e['text']) for e in payload['elements']),2000)

    def test_bad_quote_and_overlong_reader_text_never_publish(self):
        engine=self.engine()
        for flags in ({'bad_quote':True},{'long':True}):
            with self.subTest(flags=flags),tempfile.TemporaryDirectory() as tmp:
                out=Path(tmp)/'out'
                with self.assertRaises(ValueError): engine.distill(self.source(tmp),out,LightRunner(**flags))
                self.assertFalse((out/'distillation.json').exists())

    def test_upload_citation_cannot_invent_a_web_source(self):
        engine=self.engine()
        class Spoofed(LightRunner):
            def generate(self,prompt,**kwargs):
                result=super().generate(prompt,**kwargs)
                if 'STAGE:light-compose\n' in prompt:
                    result['themes'][0]['sources'][0].update(url='https://example.invalid/never-read',source_type='preview',source_id='spoof')
                return result
        with tempfile.TemporaryDirectory() as tmp:
            result=engine.distill(self.source(tmp),Path(tmp)/'out',Spoofed())
            source=result['themes'][0]['sources'][0]
            self.assertEqual(set(source),{'element_id','quote','location'})

    def test_cancellation_precedes_generation(self):
        engine=self.engine(); event=threading.Event();event.set()
        with tempfile.TemporaryDirectory() as tmp:
            runner=LightRunner()
            with self.assertRaises(InterruptedError): engine.distill(self.source(tmp),Path(tmp)/'out',runner,cancel_event=event)
            self.assertEqual(runner.calls,[])

    def test_title_has_three_stages_and_keeps_public_source_boundary(self):
        engine=self.engine()
        from distillation_result import load_bundle
        with tempfile.TemporaryDirectory() as tmp:
            runner=LightRunner(); a=engine.distill_title({'title':'测试书','author':'作者'},tmp,runner)
            self.assertEqual([s for s,_ in runner.calls],['title-identify','title-research','light-compose'])
            self.assertFalse(a['coverage']['full_text'])
            self.assertFalse(a['coverage']['complete'])
            self.assertIn('公开资料',a['coverage']['scope_note'])
            self.assertEqual(load_bundle(Path(tmp)/'distillation.json')['input_mode'],'title')

    def test_default_job_store_dispatches_light_engine(self):
        from serve_ebook import JobStore
        with tempfile.TemporaryDirectory() as tmp:
            runner=LightRunner(mode='controlled-local'); store=JobStore(tmp,runner)
            try:
                job=store.create('source.txt','先把条件弄清楚，再比较不同选择。'.encode('utf-8'))
                store.executor.submit(lambda:None).result(timeout=5)
                result=store.get(job['id'])
                self.assertEqual(result['state'],'completed',result.get('error'))
                self.assertEqual(result['analysis']['pipeline_version'],'reading-light-1')
                self.assertEqual([s for s,_ in runner.calls],['light-read','light-compose'])
            finally: store.close()

    def test_legacy_saved_jobs_keep_original_engine_when_resumed(self):
        from ebook_agent_bridge import AgentRunner
        from serve_ebook import JobStore
        import time
        with tempfile.TemporaryDirectory() as tmp:
            store=JobStore(tmp,AgentRunner())
            try:
                job=store.create('old.txt','先把条件弄清楚，再比较不同选择。'.encode('utf-8'))
                store.jobs[job['id']].pop('engine',None)
                store.agent_action(job['id'],'claim',{'session':'s','host':'test','model':'fixture'})
                runner=store.runners[job['id']]
                request=None
                for _ in range(100):
                    request=runner.next('s')
                    if request:break
                    time.sleep(.005)
                self.assertEqual(request['stage'],'stage0-map')
            finally:store.close()


if __name__=='__main__': unittest.main()
