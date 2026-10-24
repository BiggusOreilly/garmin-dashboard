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
