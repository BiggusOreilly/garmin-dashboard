"""Read-only local server integration and cross-origin protection, using an empty DB."""
import json
import multiprocessing
import tempfile
import time
import unittest
import urllib.request
import urllib.error
from companion.server import serve

class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='stride-server-test-')
        cls.port=18765
        cls.process=multiprocessing.Process(target=serve,args=(cls.tmp.name,cls.port),daemon=True)
        cls.process.start()
        for _ in range(50):
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{cls.port}/api/ping',timeout=.2).close();break
            except OSError:time.sleep(.05)
        else:raise RuntimeError('Test server did not start')
    @classmethod
    def tearDownClass(cls):
        cls.process.terminate();cls.process.join();cls.tmp.cleanup()
    def fetch(self,path='/',headers=None,method='GET'):
        return urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{self.port}'+path,headers=headers or {},method=method),timeout=5)
    def test_production_empty_and_static(self):
        with self.fetch('/api/dashboard') as r:
            d=json.load(r);self.assertEqual(d['activities'],[]);self.assertFalse(d['gpsEnabled']);self.assertFalse(d['meta']['synthetic'])
            self.assertIn("connect-src 'self'",r.headers['Content-Security-Policy']);self.assertEqual(r.headers['Cache-Control'],'no-store')
        with self.fetch('/') as r:self.assertIn(b'<title>Stride',r.read())
    def test_host_rebinding_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as c:self.fetch(headers={'Host':'attacker.example'})
        self.assertEqual(c.exception.code,403)
    def test_cross_site_refresh_rejected(self):
        for headers in [{'Origin':'https://attacker.example','X-Stride-Local':'1'},{},{'Sec-Fetch-Site':'cross-site','X-Stride-Local':'1'}]:
            with self.assertRaises(urllib.error.HTTPError) as c:self.fetch('/api/refresh',headers,method='POST')
            self.assertEqual(c.exception.code,403)
    def test_arbitrary_file_blocked(self):
        with self.assertRaises(urllib.error.HTTPError) as c:self.fetch('/../../etc/passwd')
        self.assertEqual(c.exception.code,404)
    def test_missing_run_is_404(self):
        with self.assertRaises(urllib.error.HTTPError) as c:self.fetch('/api/run/999')
        self.assertEqual(c.exception.code,404)

    def test_analysis_filters_and_missing_similarity(self):
        with self.fetch('/api/analysis?start=2026-01-01&end=2026-10-25') as r:
            data=json.load(r);self.assertEqual(data['insights'],[]);self.assertIsNone(data['recovery']['association']['r'])
        for query in ['lag=5','metric=secret','start=garbage','start=2026-10-25&end=2025-01-01']:
            with self.assertRaises(urllib.error.HTTPError) as c:self.fetch('/api/analysis?'+query)
            self.assertEqual(c.exception.code,400)
        with self.assertRaises(urllib.error.HTTPError) as c:self.fetch('/api/similar/999')
        self.assertEqual(c.exception.code,404)
    def test_classification_local_write_protection_and_validation(self):
        from companion.store import Store
        s=Store(self.tmp.name)
        s.put('activities','123',{'activityId':123,'activityName':'Synthetic test','activityType':{'typeKey':'running'},'startTimeLocal':'2026-10-01T07:00:00','distance':5000,'duration':1500})
        def post(payload,headers=None):
            return urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{self.port}/api/classification/123',data=json.dumps(payload).encode(),headers=headers or {},method='POST'),timeout=5)
        try:
            with self.assertRaises(urllib.error.HTTPError) as c:post({'classification':'Easy'})
            self.assertEqual(c.exception.code,403)
            for payload in [{'classification':'invented'},[]]:
                with self.assertRaises(urllib.error.HTTPError) as c:post(payload,{'X-Stride-Local':'1'})
                self.assertEqual(c.exception.code,400)
            with post({'classification':'Easy'},{'X-Stride-Local':'1'}) as r:self.assertTrue(json.load(r)['saved'])
            with self.fetch('/api/dashboard') as r:self.assertEqual(json.load(r)['activities'][0]['classification']['confidence'],'manual')
            with post({'classification':None},{'X-Stride-Local':'1'}) as r:self.assertTrue(json.load(r)['saved'])
        finally:
            s.db.execute("DELETE FROM records WHERE id='123'");s.db.execute("DELETE FROM derived_runs WHERE id='123'");s.db.execute("DELETE FROM run_overrides WHERE id='123'");s.db.commit();s.close()
