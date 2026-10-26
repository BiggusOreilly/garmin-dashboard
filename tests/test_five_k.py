"""Entirely synthetic turnaround, evidence hierarchy and FIT retry regression cases."""
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from companion.performance import segments,derived,progression,five_k_performance
from companion.analysis import activity,dashboard
from companion.ingest import fit_retry_due,import_activity_fit,revalidate_activity,refresh
from companion.store import Store
from companion.garmin import SafeError


def records(seconds=1800,step=1,slowdown=0,wobble=False):
    # Exactly 5,000 m; the brief near-stop consumes elapsed time, never skipped.
    speed=(5000-.1*slowdown)/(seconds-slowdown)
    result=[];distance=0
    for t in range(0,seconds+1,step):
        current=.1 if 900<=t<900+slowdown else speed
        if t:distance+=current*step
        result.append({'t':t,'distance':distance,'speed':current,'hr':152,'cadence':174,'elevation':20})
    result[-1]['distance']=5000
    if wobble:result[900]['speed']=0 # cumulative distance remains plausible
    return result


def summary(aid='1',seconds=None):
    return {'id':aid,'name':'SYNTHETIC 5K','date':'2026-10-26','distance':5000,'duration':1800,'fiveK':seconds,'zones':[]}


def analyze(rs,reported=None):
    diagnostic={};local=segments(rs,diagnostic)
    return five_k_performance(summary(seconds=reported),local.get('5 km'),diagnostic),diagnostic


class FiveKTests(unittest.TestCase):
    def test_normal_continuous_5k(self):
        p,d=analyze(records());self.assertEqual(p['evidence'],'Sensor validated');self.assertAlmostEqual(p['seconds'],1800);self.assertEqual(p['diagnostics']['invalidIntervals'],0)
    def test_turnaround_near_stop_preserves_elapsed_time(self):
        p,d=analyze(records(slowdown=4));self.assertTrue(p['eligible']);self.assertEqual(p['evidence'],'Sensor validated');self.assertAlmostEqual(p['seconds'],1800)
        self.assertEqual(p['diagnostics']['invalidDuration'],4);self.assertIn('tolerated',p['validation']);self.assertTrue(p['diagnostics']['nearStopOrTurnaroundLike'])
    def test_turnaround_with_stale_recorded_speed(self):
        rs=records(slowdown=4)
        for r in rs:
            if 900<=r['t']<904:r['speed']=3
        p,d=analyze(rs);self.assertTrue(p['eligible'])
    def test_isolated_gps_speed_wobble(self):
        p,d=analyze(records(wobble=True));self.assertTrue(p['eligible']);self.assertIn('wobble tolerated',p['validation']);self.assertEqual(p['diagnostics']['invalidIntervals'],1)
    def test_fractional_turnaround_diagnostic(self):
        rs=records();pause={**rs[900],'t':903.2,'distance':2500.1,'speed':.1/3.2}
        for r in rs[901:]:r['t']+=3.2
        rs.insert(901,pause)
        p,d=analyze(rs);self.assertTrue(p['eligible']);self.assertAlmostEqual(p['diagnostics']['invalidDuration'],3.2)
        self.assertAlmostEqual(p['seconds'],1803.2)
    def test_sustained_stop_rejected(self):
        p,d=analyze(records(slowdown=30));self.assertFalse(p['eligible']);self.assertIn('stationary',p['validation']);self.assertGreater(p['diagnostics']['invalidDuration'],12)
    def test_gps_teleport_still_rejected_even_with_garmin(self):
        rs=records()
        for r in rs:
            if r['t']>=900:r['distance']+=1000
        p,d=analyze(rs,1609);self.assertEqual(p['evidence'],'Flagged');self.assertFalse(p['eligible']);self.assertIn('teleport',p['validation'])
    def test_distance_reset_rejected(self):
        rs=records();rs[900]['distance']=0
        p,d=analyze(rs,1609);self.assertEqual(p['evidence'],'Flagged');self.assertFalse(p['eligible']);self.assertTrue(p['diagnostics']['distanceDecreased']);self.assertIn('reset',p['validation'])
    def test_recording_gap_not_tolerated_as_sensor_validated(self):
        rs=records()
        for r in rs:
            if r['t']>=900:r['t']+=47
        p,d=analyze(rs);self.assertFalse(p['eligible']);self.assertIn('48 s recording gap',p['validation'])
        p,d=analyze(rs,1609);self.assertTrue(p['eligible']);self.assertEqual(p['evidence'],'Garmin reported');self.assertIn('48 s',p['validation'])
    def test_garmin_no_stream_can_be_pb(self):
        p,d=analyze([],1609);self.assertEqual(p['evidence'],'Garmin reported');self.assertIn('unavailable',p['validation'])
        r=summary();r['fiveKPerformance']=p
        self.assertEqual(progression([r])['5 km'][0]['seconds'],1609)
    def test_faster_garmin_beats_slower_validated(self):
        p,d=analyze(records(),1609);self.assertEqual(p['seconds'],1609);self.assertEqual(p['evidence'],'Garmin reported');self.assertIsNone(p['hr']);self.assertEqual(p['splits'],[])
    def test_faster_validated_beats_slower_garmin(self):
        p,d=analyze(records(),1900);self.assertEqual(p['seconds'],1800);self.assertEqual(p['evidence'],'Sensor validated')
    def test_same_performance_deduplicates_and_upgrades(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(tmp);r=summary(seconds=1800);first=derived(s,r);self.assertEqual(first['fiveKPerformance']['evidence'],'Garmin reported')
            s.put('series','1',{'records':records()});new=derived(s,r);self.assertEqual(new['fiveKPerformance']['evidence'],'Sensor validated')
            r.update(new);self.assertEqual(len(progression([r])['5 km']),1);s.close()
    def test_impossible_reported_pace_flagged(self):
        p,d=analyze([],200);self.assertFalse(p['eligible']);self.assertEqual(p['evidence'],'Flagged')
    def test_small_sampling_gap_remains_inconclusive_not_invalid_garmin(self):
        rs=records()
        for r in rs:
            if r['t']>=900:r['t']+=10
        p,d=analyze(rs,1609);self.assertEqual(p['evidence'],'Garmin reported');self.assertIn('11 s recording gap',p['validation'])
    def test_excess_isolated_anomalies_not_clean(self):
        rs=records()
        for i in [100,200,300,400]:rs[i]['speed']=0
        p,d=analyze(rs);self.assertFalse(p['eligible'])
    def test_summary_from_detail_and_old_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(tmp);s.put('activities','1',{'activityId':1,'activityName':'SYNTHETIC','startTimeLocal':'2026-10-26T08:00:00','distance':5000,'duration':1700,'activityType':{'typeKey':'running'},'fastestSplit_5000':1609})
            s.db.execute('INSERT INTO derived_runs VALUES(?,?,?)',('1','OLD_ANALYSIS', '{}'));s.db.commit()
            data=dashboard(s);self.assertEqual(data['records']['5 km'][0]['seconds'],1609);self.assertEqual(len(data['activities']),1)
            self.assertEqual(activity({'activityId':1},{'summaryDTO':{'fastestSplit_5000':1609}})['fiveK'],1609);s.close()
    def test_sensor_metrics_not_blocked_by_missing_hr_cadence(self):
        rs=records()
        for r in rs:r['hr']=None;r['cadence']=None
        p,d=analyze(rs);self.assertTrue(p['eligible']);self.assertIsNone(p['hr']);self.assertIsNone(p['cadence'])

    def test_tolerance_at_five_second_sampling(self):
        p,d=analyze(records(step=5,slowdown=5));self.assertTrue(p['eligible']);self.assertAlmostEqual(p['seconds'],1800)
    def test_rounded_corroboration_retains_best_credible_time(self):
        p,d=analyze(records(),1799);self.assertTrue(p['eligible']);self.assertEqual(p['evidence'],'Sensor validated');self.assertEqual(p['seconds'],1799);self.assertEqual(p['sensorSeconds'],1800)

    def test_bad_speed_field_alone_does_not_disprove_garmin_distance_result(self):
        rs=records(step=5)
        for r in rs:r['speed']=10
        p,d=analyze(rs,1609);self.assertEqual(p['evidence'],'Garmin reported');self.assertTrue(p['eligible']);self.assertIn('sensor speed',p['validation'])

    def test_small_cumulative_distance_wobble_at_turn_remains_valid(self):
        rs=records();rs[900]['distance']+=1.8
        p,d=analyze(rs);self.assertTrue(p['eligible']);self.assertEqual(p['evidence'],'Sensor validated');self.assertEqual(p['diagnostics']['invalidIntervals'],2)


class FitRetryTests(unittest.TestCase):
    def test_missing_empty_and_incomplete_series_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(tmp);item={'distance':5000}
            self.assertTrue(fit_retry_due(s,'1',item));s.put('series','1',{'records':[]});self.assertTrue(fit_retry_due(s,'1',item))
            s.put('series','1',{'records':records()[:100]});self.assertTrue(fit_retry_due(s,'1',item));s.close()
    def test_healthy_history_is_not_downloaded_repeatedly(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(tmp);s.put('series','1',{'records':records()});self.assertFalse(fit_retry_due(s,'1',{'distance':5000}));self.assertFalse(fit_retry_due(s,'1',{'distance':5000}))
            self.assertTrue(fit_retry_due(s,'1',{'distance':5100}));self.assertTrue(fit_retry_due(s,'1',{'distance':5000},force=True));s.close()
    def test_reparse_local_original_before_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(tmp);folder=Path(tmp)/'fit';folder.mkdir();(folder/'1.zip').write_bytes(b'SYNTHETIC')
            from unittest.mock import MagicMock
            api=MagicMock()
            with patch('companion.ingest.parse_fit',return_value={'records':records()}):import_activity_fit(s,api,'1',{'distance':5000})
            api.call.assert_not_called();self.assertEqual(s.meta('fit:1')['state'],'usable');s.close()
    def test_failed_parse_backoff_and_explicit_retry_preserves_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            from unittest.mock import MagicMock
            s=Store(tmp);previous={'records':records()[:100]};s.put('series','1',previous);api=MagicMock();api.call.return_value=b'SYNTHETIC'
            with patch('companion.ingest.parse_fit',side_effect=ValueError('private details')):
                with self.assertRaises(SafeError):import_activity_fit(s,api,'1',{'distance':5000})
            self.assertEqual(s.get('series','1'),previous);self.assertFalse(fit_retry_due(s,'1',{'distance':5000}));self.assertTrue(fit_retry_due(s,'1',{'distance':5000},force=True))
            self.assertTrue(fit_retry_due(s,'1',{'distance':5000},current=datetime.now(timezone.utc)+timedelta(days=2)))
            with patch('companion.ingest.parse_fit',return_value={'records':records()}):import_activity_fit(s,api,'1',{'distance':5000},force_download=True)
            self.assertEqual(s.meta('fit:1')['state'],'usable');s.close()
    def test_empty_reparse_does_not_replace_better_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            from unittest.mock import MagicMock
            s=Store(tmp);old={'records':records()[:500]};s.put('series','1',old);api=MagicMock();api.call.return_value=b'SYNTHETIC'
            with patch('companion.ingest.parse_fit',return_value={'records':[]}):
                with self.assertRaises(SafeError):import_activity_fit(s,api,'1',{'distance':5000},force_download=True)
            self.assertEqual(s.get('series','1'),old);s.close()
    def test_explicit_revalidation_only_downloads_selected_activity(self):
        with tempfile.TemporaryDirectory() as tmp:
            from unittest.mock import MagicMock
            s=Store(tmp);item={'activityId':1,'activityType':{'typeKey':'running'},'distance':5000};s.put('activities','1',item);api=MagicMock();api.call.return_value=b'SYNTHETIC'
            with patch('companion.ingest.parse_fit',return_value={'records':records()}):revalidate_activity(s,'1',api=api)
            api.call.assert_called_once_with('download_activity','1');self.assertEqual(s.meta('fit:1')['state'],'usable')
            s.meta('synthetic',True)
            with self.assertRaises(SafeError):revalidate_activity(s,'1',api=api)
            s.close()

    def test_just_short_of_reported_5k_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(tmp);s.put('series','1',{'records':records()[:-2]});self.assertTrue(fit_retry_due(s,'1',{'distance':5000,'fastestSplit_5000':1609}));s.close()
    def test_normal_refresh_does_not_redownload_unchanged_healthy_fit(self):
        from test_ingest import FakeAPI
        class RunningAPI(FakeAPI):
            def call(self,method,*args,**kw):
                if method=='search_activities':
                    self.calls.append((method,args,kw))
                    return [{'activityId':1,'activityType':{'typeKey':'running'},'startTimeLocal':'2026-01-01T08:00:00','distance':5000}] if kw['start']==0 else []
                if method=='download_activity':self.calls.append((method,args,kw));return b'SYNTHETIC'
                return super().call(method,*args,**kw)
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(tmp);api=RunningAPI()
            with patch('companion.ingest.parse_fit',return_value={'records':records()}):
                refresh(s,api,today=date(2026,1,2));refresh(s,api,today=date(2026,1,2))
                self.assertEqual(sum(c[0]=='download_activity' for c in api.calls),1)
                refresh(s,api,today=date(2026,1,2),revalidate_all=True)
                self.assertEqual(sum(c[0]=='download_activity' for c in api.calls),2)
            s.close()

    def test_invalid_replacement_keeps_healthy_cache_and_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            from unittest.mock import MagicMock
            s=Store(tmp);old={'records':records()};s.put('series','1',old)
            original=Path(tmp)/'fit'/'1.zip';original.parent.mkdir();original.write_bytes(b'GOOD_SYNTHETIC')
            api=MagicMock();api.call.return_value=b'BAD_SYNTHETIC'
            with patch('companion.ingest.parse_fit',return_value={'records':[]}):
                with self.assertRaises(SafeError):import_activity_fit(s,api,'1',{'distance':5000},force_download=True)
            self.assertEqual(s.get('series','1'),old);self.assertEqual(original.read_bytes(),b'GOOD_SYNTHETIC');s.close()
    def test_changed_summary_bypasses_old_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            from unittest.mock import MagicMock
            s=Store(tmp);s.put('series','1',{'records':records()});fit_retry_due(s,'1',{'distance':5000})
            original=Path(tmp)/'fit'/'1.zip';original.parent.mkdir();original.write_bytes(b'OLD_SYNTHETIC')
            api=MagicMock();api.call.return_value=b'NEW_SYNTHETIC'
            with patch('companion.ingest.parse_fit',return_value={'records':records()}):import_activity_fit(s,api,'1',{'distance':5000,'activityName':'Edited'})
            api.call.assert_called_once_with('download_activity','1');self.assertEqual(original.read_bytes(),b'NEW_SYNTHETIC');s.close()
