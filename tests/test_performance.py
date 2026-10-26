"""Known synthetic examples only; never use an athlete's files."""
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from companion.quality import clean_intervals, report
from companion.performance import bands, segments, classify, similar, volume, progression, correlation, insights, derived, trend
from companion.analysis import drift, dashboard, detail_metrics
from companion.store import Store


def stream(speed=3, hr=152, length=3600, step=5):
    return [{'t':t,'distance':t*speed,'speed':speed,'hr':hr,'cadence':174,'elevation':20} for t in range(0,length+1,step)]


def run(aid='1', d='2026-10-20', distance=10800):
    return {'id':aid,'date':d,'name':'Synthetic run','type':'running','distance':distance,'duration':distance/3,'pace':1000/3,'hr':152,'cadence':174,'elevation':0,'zones':[100,2800,500,100,0]}


class PerformanceTests(unittest.TestCase):
    def test_band_known_time_weighted(self):
        b=bands(stream())
        self.assertAlmostEqual(b['hr']['150']['value'],1000/3)
        self.assertAlmostEqual(b['pace']['330']['value'],152)
        self.assertEqual(b['hr']['150']['seconds'],3000)
    def test_band_missing_hr_and_tiny_samples(self):
        rs=stream(hr=None)
        self.assertEqual(bands(rs),{'hr':{},'pace':{}})
        self.assertEqual(bands(stream(length=720)),{'hr':{},'pace':{}})
    def test_band_excludes_warmup_and_transients(self):
        rs=stream()
        for r in rs:
            r['hr']=152 if r['t']<600 or r['t']%30<15 else 170
        self.assertNotIn('150',bands(rs)['hr'])
    def test_half_open_bands(self):
        b=bands(stream(hr=155));self.assertNotIn('150',b['hr']);self.assertIn('155',b['hr'])
    def test_pauses_and_gps_spikes(self):
        rs=stream()
        for r in rs:
            if r['t']>600:r['distance']+=10000
        self.assertLess(report(rs)['seconds'],3600)
        self.assertNotIn('5 km',segments(rs[:400]))
        self.assertEqual(segments(stream(speed=0)),{})
    def test_quality_hr_spikes_and_cadence(self):
        rs=stream();rs[100]['hr']=230;rs[101]['cadence']=500
        q=clean_intervals(rs)
        self.assertIsNone(q[99]['hr']);self.assertIsNone(q[100]['cadence'])
        self.assertIsNone(drift(stream(hr=None))['value'])
    def test_known_records_and_short_sampling(self):
        best=segments(stream())
        self.assertAlmostEqual(best['5 km']['seconds'],5000/3)
        self.assertAlmostEqual(best['1 mile']['seconds'],1609.344/3)
        self.assertEqual(best['5 km']['hr'],152)
        self.assertNotIn('400 m',best)
        self.assertAlmostEqual(segments(stream(step=1))['400 m']['seconds'],400/3)
    def test_record_missing_hr_does_not_invent(self):
        r=segments(stream(hr=None))['5 km'];self.assertIsNone(r['hr']);self.assertIsNone(r['maxHR'])
    def test_downhill_flag(self):
        rs=stream()
        for r in rs:r['elevation']=100-r['distance']*.02
        self.assertIn('Downhill',segments(rs)['5 km']['flag'])
    def test_reset_gap_and_short_record(self):
        rs=stream();rs[100]['distance']=0
        self.assertEqual(segments(rs),{})
        self.assertEqual(segments(stream(length=60)),{})
        self.assertEqual(segments(stream(step=30)),{})
    def test_paused_records_excluded(self):
        rs=stream(length=1800)
        for r in rs:
            if r['t']>=900:r['t']+=120
        self.assertNotIn('5 km',segments(rs))
    def test_pb_history_improvement_and_flag(self):
        a,b,c=run('1','2026-01-01'),run('2','2026-02-01'),run('3','2026-03-01')
        for r,v in [(a,1800),(b,1750),(c,1700)]:r['records']={'5 km':{'seconds':v,'flag':None}}
        c['records']['5 km']['flag']='Downhill'
        ev=progression([b,c,a])['5 km'];self.assertEqual(len(ev),2);self.assertEqual(ev[-1]['improvement'],50)
    def test_classification_uses_zone_evidence(self):
        r=run();r['zones']=[10,10,10,2000,100]
        c=classify(r,stream());self.assertEqual(c['label'],'Threshold');self.assertIn('65%',c['reason'])
        r['zones']=[];self.assertEqual(classify(r,[])['label'],'Mixed / unclassified')
    def test_interval_structure(self):
        rs=stream()
        distance=0
        for r in rs:
            r['speed']=4 if int(r['t']//120)%2 else 2
            distance+=r['speed']*5;r['distance']=distance
        self.assertEqual(classify(run(),rs)['label'],'Intervals')
    def test_similar_runs_lengths_and_future_excluded(self):
        a=run('2');b=run('1','2026-10-01',10000);c=run('3','2026-10-21');d=run('4',distance=3000)
        matches=similar(a,[a,b,c,d]);self.assertEqual([m['id'] for m in matches],['1']);self.assertEqual(matches[0]['assessment'],'Similar')
    def test_rolling_volume_known_and_rest_days(self):
        a=run('1','2026-10-01',10000);b=run('2','2026-10-08',5000)
        v=volume([a,b],end='2026-10-08')
        self.assertEqual(v['daily'][-1]['rolling7'],5)
        self.assertEqual(v['daily'][-1]['rolling28'],15)
        self.assertEqual(v['daily'][1]['km'],0)
        self.assertEqual(sum(x['count'] for x in v['weekly']),2)
    def test_volume_change_and_abrupt_flag(self):
        rs=[run(str(i),f'2026-09-{7+i*7:02}',10000) for i in range(4)]
        rs.append(run('5','2026-10-05',15000))
        w=volume(rs,'2026-10-11')['weekly'][-1]
        self.assertEqual(w['change'],50);self.assertTrue(w['abrupt']);self.assertEqual(w['baseline'],10)
    def test_recovery_correlations(self):
        self.assertIsNone(correlation([(1,2)])['r'])
        self.assertEqual(correlation([(i,i*2) for i in range(10)])['r'],1)
        self.assertEqual(correlation([(i,-i) for i in range(10)])['r'],-1)
        self.assertIsNone(correlation([(1,2)]*12)['r'])
    def test_insights_require_adequate_samples(self):
        self.assertEqual(insights([],[],{'weekly':[]},'2026-10-25'),[])
        rs=[]
        for i,d in enumerate(['2026-09-05','2026-09-10','2026-09-15','2026-10-05','2026-10-10','2026-10-15']):
            r=run(str(i),d);r['bands']={'hr':{'150':{'value':360 if i<3 else 345}}};rs.append(r)
        obs=insights(rs,[],{'weekly':[]},'2026-10-25')
        self.assertEqual(len(obs),1);self.assertIn('15 sec/km faster',obs[0]['text']);self.assertIn('3 recent',obs[0]['evidence'])
    def test_migrate_existing_database_and_cache_invalidation(self):
        with tempfile.TemporaryDirectory() as directory:
            db=sqlite3.connect(directory+'/dashboard.sqlite3');db.executescript('CREATE TABLE records(dataset TEXT,id TEXT,payload TEXT NOT NULL,fetched TEXT NOT NULL,PRIMARY KEY(dataset,id));CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);')
            db.execute('INSERT INTO metadata VALUES(?,?)',('sentinel',json.dumps('kept')));db.commit();db.close()
            s=Store(directory);self.assertEqual(s.meta('sentinel'),'kept');self.assertEqual(s.db.execute('PRAGMA user_version').fetchone()[0],2)
            s.put('series','1',{'records':stream()});r=run();first=derived(s,r)
            with patch('companion.performance.segments',side_effect=AssertionError('Unexpected recompute')):self.assertEqual(derived(s,r),first)
            s.put('series','1',{'records':stream(hr=145)})
            self.assertNotEqual(derived(s,r)['bands'],first['bands']);s.close()
    def test_decoupling_components_and_matched_pace(self):
        rs=stream();
        for r in rs:
            if r['t']>2100:r['hr']=160
        d=drift(rs);self.assertAlmostEqual(d['value'],5);self.assertAlmostEqual(d['hrAtPaceChange'],8)
        self.assertAlmostEqual(d['firstEfficiency'],3/152);self.assertAlmostEqual(d['secondEfficiency'],3/160)
        self.assertIsNone(d['paceAtHRChange'])
    def test_trend_windows_and_missing_samples(self):
        p=[{'date':'2026-10-02','value':10}]
        self.assertIsNone(trend(p,'2026-10-25')['change'])


    def test_recovery_lag_and_daily_pairing(self):
        from companion.performance import recovery_analysis
        rs=[run(str(i),f'2026-10-{i+2:02}') for i in range(10)]
        for i,r in enumerate(rs):r['bands']={'pace':{'330':{'value':140+i}}}
        days=[{'date':f'2026-10-{i+1:02}','hrv':50+i,'sleep':25000} for i in range(11)]
        response=recovery_analysis(rs,days,volume(rs,'2026-10-11'),'hrv','performance',1)
        self.assertEqual(response['association']['n'],10);self.assertEqual(response['association']['r'],1)
        self.assertEqual(response['points'][1]['x'],50)
    def test_chart_projection_is_bounded_and_coordinate_free(self):
        from companion.quality import chart_series
        rs=stream(step=1);rs[0]['position_lat']=123;rs[1]['hr']=230
        result=chart_series({'records':rs,'laps':[{'gps':'ignored'}]},limit=100)
        self.assertLessEqual(len(result['records']),101);self.assertEqual(result['laps'],[])
        self.assertNotIn('position_lat',str(result));self.assertTrue(result['displaySampled'])
    def test_missing_cadence_does_not_prevent_hr_bands(self):
        rs=stream()
        for r in rs:r['cadence']=None
        self.assertIn('150',bands(rs)['hr']);self.assertIsNone(detail_metrics({'records':rs})['cadenceChange'])

    def test_partial_recording_is_disclosed(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(d);s.put('series','1',{'records':stream(length=1800)})
            result=derived(s,run())
            self.assertTrue(any('Incomplete sensor recording' in x for x in result['quality']['issues']));s.close()

    def test_rhr_insight_uses_calendar_baseline(self):
        from datetime import date,timedelta
        days=[{'date':(date(2026,10,25)-timedelta(days=30-i)).isoformat(),'rhr':50 if i<28 else 56} for i in range(31)]
        found=insights([],days,{'weekly':[],'daily':[]},'2026-10-25')
        self.assertTrue(any(x['id']=='rhr' for x in found))
        for d in days[:28]:d['date']='2025'+d['date'][4:]
        self.assertFalse(any(x['id']=='rhr' for x in insights([],days,{'weekly':[],'daily':[]},'2026-10-25')))

if __name__=='__main__':unittest.main()
