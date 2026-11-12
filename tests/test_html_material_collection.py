import sys,json,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reading-yearbook-skill/scripts'))
from collect_html_materials import call, reviews, download_cover, collect
from collect_weread_data import WeReadError


class MaterialCollectionTests(unittest.TestCase):
    def test_valid_cache_reuses_without_network_or_credentials_in_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache=Path(tmp)/'cache.json'
            with patch('collect_html_materials.gateway_call',return_value={'updated':[]}):
                call('/book/bookmarklist',{},'secret',cache,threading.Event())
            with patch('collect_html_materials.gateway_call') as request:
                self.assertEqual(call('/book/bookmarklist',{},'secret',cache,threading.Event()),{'updated':[]})
                request.assert_not_called()

    def test_cache_is_bound_to_all_parameters_and_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache=Path(tmp)/'notebooks-1.json'
            replies=[{'books':[{'sort':10}]},{'books':[{'sort':20}]},{'books':[{'sort':30}]}]
            with patch('collect_html_materials.gateway_call',side_effect=replies) as request:
                for key, cursor, reply in zip(('key-a','key-a','key-b'), (10,20,20), replies):
                    self.assertEqual(call('/user/notebooks',{'count':50,'lastSort':cursor},key,cache,threading.Event()),reply)
                self.assertEqual(request.call_count,3)

    def test_standalone_collection_reloads_notes_and_progress_for_another_account(self):
        data={'year':2026,'books':[{'book_id':'one','title':'Shared book'}]}
        def reply(api, params, key, **kwargs):
            return {
                '/book/info': {'title':'Shared book'},
                '/book/getprogress': {'book': {'progress': 20 if key=='key-a' else 60}},
                '/book/bookmarklist': {'updated': []},
                '/review/list/mine': {'reviews':[{'content':'first thought' if key=='key-a' else 'second thought'}]},
            }[api]
        with tempfile.TemporaryDirectory() as tmp, patch('collect_html_materials.gateway_call',side_effect=reply) as request, patch('builtins.print'):
            collect(data,{},tmp,'key-a')
            collect(data,{},tmp,'key-b')
            row=json.loads((Path(tmp)/'materials.json').read_text('utf-8'))['books'][0]
            self.assertEqual(request.call_count,8)
            self.assertEqual(row['progress'],60)
            self.assertEqual([n['text'] for n in row['thoughts']],['second thought'])

    def test_auth_failure_stops_and_does_not_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache=Path(tmp)/'cache.json';stopped=threading.Event()
            with patch('collect_html_materials.gateway_call',side_effect=WeReadError('HTTP 403')):
                with self.assertRaises(WeReadError):call('/book/info',{},'secret',cache,stopped)
            self.assertTrue(stopped.is_set());self.assertFalse(cache.exists())

    def test_review_pagination_collects_all_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('collect_html_materials.call',side_effect=[{'reviews':[{'review':{'content':'a'}}],'hasMore':1,'synckey':10}, {'reviews':[{'review':{'content':'b'}}],'hasMore':0}]):
                self.assertEqual(len(reviews('one','secret',Path(tmp)/'r.json',threading.Event())['reviews']),2)

    def test_review_repeated_cursor_and_malformed_response_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            for reply in [{'reviews':[],'hasMore':1,'synckey':0},{'hasMore':0}]:
                with patch('collect_html_materials.call',return_value=reply):
                    with self.assertRaises(WeReadError):reviews('one','secret',Path(tmp)/'r.json',threading.Event())

    def test_unverified_cover_origin_is_not_downloaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('collect_html_materials.urllib.request.urlopen') as request:
                with self.assertRaises(ValueError):download_cover('https://example.org/private',Path(tmp)/'c.image')
                request.assert_not_called()

    def test_unbound_legacy_thoughts_are_recollected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);legacy=root/'legacy';legacy.mkdir()
            (legacy/'one-thoughts.json').write_text('{"reviews":[{"content":"unbound"}]}',encoding='utf-8')
            with patch('collect_html_materials.call',side_effect=[{'title':'示例书'}, {'book':{'progress':50}}, {'updated':[]}, {'reviews':[{'content':'verified'}]}]), patch('builtins.print'):
                collect({'year':2026,'books':[{'book_id':'one','title':'示例书'}]}, {}, root/'output','secret',legacy)
            row=json.loads((root/'output/materials.json').read_text('utf-8'))['books'][0]
            self.assertEqual(row['collection']['thoughts'],'complete')
            self.assertEqual([n['text'] for n in row['thoughts']],['verified'])


if __name__=='__main__':unittest.main()
