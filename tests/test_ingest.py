from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,MagicMock
from companion.ingest import refresh,windows,range_fetch,strip_location,validate_payload
from companion.garmin import SafeError,Garmin
from companion.store import Store

class FakeAPI:
    def __init__(self,partial=False):self.calls=[];self.partial=partial
    def call(self,method,*args,**kw):
        self.calls.append((method,args,kw))
        if method=='search_activities':
            # Server may cap page size below requested 99.
            return [{'activityId':kw['start']+1,'startTimeLocal':'2026-01-01T08:00:00','activityType':{'typeKey':'cycling'},'distance':5000,'duration':1200,'startLatitude':-33}] if kw['start']<2 else []
        if method=='get_activity':return {'summaryDTO':{'distance':5000,'duration':1200,'startTimeLocal':'2026-01-01T08:00:00'}}
        if self.partial and method=='get_daily_hrv_summaries':raise SafeError('Unavailable',404)
        if method in ('get_daily_summaries',):return {'data':[]}
        if method=='get_daily_hrv_summaries':return {'hrvSummaries':[]}
        if method=='get_weight_measurements':return {'dailyWeightSummaries':[]}
        return []
    def close(self):pass

class IngestTests(unittest.TestCase):
    def test_incompatible_schema_rejected_without_false_success(self):
        with self.assertRaises(SafeError):validate_payload('daily',{'renamedData':[]})
        validate_payload('daily',{'data':[],'newOptionalField':True})
        validate_payload('sleep',None)
    def test_windows_inclusive(self):
        a=list(windows(date(2026,1,1),date(2026,3,1),28))
        self.assertEqual(a,[('2026-01-01','2026-01-28'),('2026-01-29','2026-02-25'),('2026-02-26','2026-03-01')])
    def test_split_rejected_ranges(self):
        class API:
            def call(self,m,a,b):
                if a!=b:raise SafeError('limit',400)
                return []
        result=range_fetch(API(),'m','2026-01-01','2026-01-04')
        self.assertEqual(len(result),4)
    def test_pagination_and_incremental(self):
        with tempfile.TemporaryDirectory() as p:
            s=Store(p);a=FakeAPI();refresh(s,a,today=date(2026,1,2))
            self.assertEqual(len(s.all('activities')),2)
            self.assertNotIn('startLatitude',s.all('activities')[0]);self.assertIsNotNone(s.meta('last_success'))
            a.calls=[];refresh(s,a,today=date(2026,1,3))
            self.assertEqual(a.calls[0][2]['start_date'],'2025-12-19');s.close()
    def test_partial_never_marked_full_success(self):
        with tempfile.TemporaryDirectory() as p:
            s=Store(p);refresh(s,FakeAPI(True),today=date(2026,1,2))
            self.assertIsNone(s.meta('last_success'));self.assertEqual(s.meta('datasets')['hrv']['state'],'partial');self.assertIsNone(s.meta('cursor:hrv'));self.assertIsNotNone(s.meta('last_completed'));s.close()
    def test_repeated_page_stops(self):
        class Repeated(FakeAPI):
            def call(self,m,*args,**kw):
                if m=='search_activities':kw['start']=0
                return super().call(m,*args,**kw)
        with tempfile.TemporaryDirectory() as p:
            s=Store(p)
            with self.assertRaises(SafeError):refresh(s,Repeated(),today=date(2026,1,2))
            self.assertIsNone(s.meta('activities_through'));s.close()
    def test_gps_projection(self):
        self.assertEqual(strip_location({'latitude':0,'x':[{'endLongitude':0,'hr':140}]}),{'x':[{'hr':140}]})
    def test_401_refresh_and_retry(self):
        from garmin_personal_api import HttpError
        g=object.__new__(Garmin);g.key='SYNTHETIC_TEST_KEY';g.auth=MagicMock();g.client=MagicMock()
        g.client.get_activity.side_effect=[HttpError(status_code=401,method='GET',url='https://personal.connectapi.garmin.com',response_text='synthetic'),{'activityId':1}]
        self.assertEqual(g.call('get_activity',1),{'activityId':1})
        self.assertTrue(any(c.kwargs.get('force_refresh') for c in g.auth.obtain_token.call_args_list))

if __name__=='__main__':unittest.main()
