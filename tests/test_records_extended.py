"""Invented distances/times only; official summary splits never inferred from distance."""
import tempfile
import unittest
from companion.performance import segments,derived,progression
from companion.analysis import activity,dashboard
from companion.store import Store

def samples(length=10000,seconds=3600,slow=0,step=5):
    speed=(length-.1*slow)/(seconds-slow);out=[];d=0
    for t in range(0,seconds+1,step):
        v=.1 if seconds/2<=t<seconds/2+slow else speed
        if t:d+=v*step
        out.append({'t':t,'distance':d,'speed':v,'hr':150,'cadence':171,'elevation':30})
    out[-1]['distance']=length
    return out

def run(rs,reported=None,distance=10000):
    with tempfile.TemporaryDirectory() as tmp:
        s=Store(tmp);s.put('series','1',{'records':rs})
        r={'id':'1','date':'2026-11-05','start':'2026-11-05T08:00:00','name':'Synthetic 10K','distance':distance,'duration':3600,'tenK':reported,'zones':[]}
        r.update(derived(s,r));s.close();return r

class ExtendedRecordsTests(unittest.TestCase):
    def test_clean_10k(self):
        r=run(samples());p=r['recordPerformances']['10 km'];self.assertTrue(p['eligible']);self.assertEqual(p['evidence'],'Sensor validated');self.assertAlmostEqual(p['seconds'],3600)
    def test_10k_u_turn(self):
        r=run(samples(slow=5));p=r['recordPerformances']['10 km'];self.assertTrue(p['eligible']);self.assertIn('tolerated',p['validation']);self.assertAlmostEqual(p['seconds'],3600)
    def test_10k_isolated_gps_wobble(self):
        rs=samples();rs[300]['speed']=0
        self.assertTrue(run(rs)['recordPerformances']['10 km']['eligible'])
    def test_brief_slowdown_at_one_second_sampling(self):
        self.assertTrue(run(samples(slow=4,step=1))['recordPerformances']['10 km']['eligible'])
    def test_sustained_pause_rejected(self):
        self.assertFalse(run(samples(slow=30))['recordPerformances']['10 km']['eligible'])
    def test_recording_gap_rejected(self):
        rs=samples()
        for r in rs:
            if r['t']>=1800:r['t']+=40
        p=run(rs)['recordPerformances']['10 km'];self.assertFalse(p['eligible']);self.assertIn('gap',p['validation'])
    def test_gps_teleport_rejected(self):
        rs=samples()
        for r in rs:
            if r['t']>=1800:r['distance']+=2000
        p=run(rs,3300)['recordPerformances']['10 km'];self.assertFalse(p['eligible']);self.assertIn('teleport',p['validation'])
    def test_reset_rejected(self):
        rs=samples();rs[300]['distance']=0
        p=run(rs,3300)['recordPerformances']['10 km'];self.assertFalse(p['eligible']);self.assertIn('reset',p['validation'])
    def test_garmin_exact_10k(self):
        item={'activityId':1,'fastestSplit_10000':3300}
        self.assertEqual(activity(item)['tenK'],3300)
        p=run([],3300)['recordPerformances']['10 km'];self.assertTrue(p['eligible']);self.assertEqual(p['evidence'],'Garmin reported');self.assertEqual(p['seconds'],3300);self.assertIsNone(p['hr'])
    def test_near_10k_summary_not_an_exact_record(self):
        r=run([],distance=9986)
        self.assertNotIn('10 km',r['recordPerformances']);self.assertIn('10K recorded',r['recordEfforts']['10 km']['validation']);self.assertEqual(progression([r])['10 km'],[])
    def test_marginally_over_distance_needs_stream_or_explicit_split(self):
        r=run([],distance=10019);self.assertIn('10 km',r['recordEfforts']);self.assertEqual(progression([r])['10 km'],[])
    def test_first_pb_and_slower_history(self):
        a=run(samples());b=run(samples(seconds=3700));b.update(id='2',date='2026-11-06')
        history=progression([a,b])['10 km'];self.assertEqual(len(history),1);self.assertEqual(history[0]['id'],'1');self.assertIn('10 km',b['recordPerformances'])
    def test_shorter_distance_limits_not_weakened_by_long_run_budget(self):
        self.assertNotIn('1 km',segments(samples(1000,360,slow=10,step=1)))
        self.assertIn('1 km',segments(samples(1000,360,slow=2,step=1)))
        self.assertNotIn('400 m',segments(samples(400,120,slow=2,step=1)))
    def test_all_common_distances_have_appropriate_tolerance(self):
        for label,length in [('1 km',1000),('1 mile',1609.344),('3 km',3000),('5 km',5000),('10 km',10000)]:
            with self.subTest(label=label):self.assertIn(label,segments(samples(length,360 if length<2000 else 1800 if length<=5000 else 3600,slow=2,step=1)))
    def test_existing_cache_recalculated_without_deleting_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(tmp);s.put('activities','1',{'activityId':1,'activityType':{'typeKey':'running'},'distance':10000,'duration':3600,'fastestSplit_10000':3300,'startTimeLocal':'2026-11-05T08:00:00'})
            s.db.execute('INSERT INTO derived_runs VALUES(?,?,?)',('1','version-seven','{}'));s.db.commit()
            self.assertEqual(dashboard(s)['records']['10 km'][0]['seconds'],3300);self.assertIsNotNone(s.get('activities','1'));s.close()
