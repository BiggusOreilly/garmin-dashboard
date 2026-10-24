"""Synthetic fixtures only. No Garmin account or real records."""
import tempfile
import unittest
from companion.analysis import drift,detail_metrics,activity,health,dashboard,num
from companion.store import Store

class AnalysisTests(unittest.TestCase):
    def series(self,hr=140,speed=3):
        return [{'t':t,'distance':t*speed,'speed':speed,'hr':hr,'cadence':174,'elevation':20} for t in range(0,3601,5)]
    def test_steady_decoupling_zero(self):
        self.assertAlmostEqual(drift(self.series())['value'],0)
    def test_known_decoupling_and_hr_change(self):
        r=self.series()
        for x in r:
            if x['t']>2100:x['hr']=154
        self.assertAlmostEqual(drift(r)['value'],100*(1-140/154),places=5)
        self.assertAlmostEqual(drift(r)['hrChange'],10,places=5)
    def test_missing_hr_not_zero(self):
        r=self.series()
        for x in r:x['hr']=None
        self.assertIsNone(drift(r)['value'])
    def test_short_run_and_gaps(self):
        self.assertIsNone(drift(self.series()[:100])['value'])
        self.assertIsNone(drift(self.series()[::10])['value'])
    def test_variable_speed_suppressed(self):
        r=self.series()
        for i,x in enumerate(r):x['speed']=2 if i%2 else 4
        self.assertIsNone(drift(r)['value'])
    def test_splits_interpolated(self):
        m=detail_metrics({'records':self.series()})
        self.assertEqual(len(m['splits']),10)
        self.assertAlmostEqual(m['splits'][0]['pace'],1000/3)
        self.assertAlmostEqual(m['splitCV'],0)
        self.assertAlmostEqual(m['splitChange'],0)
    def test_schema_and_units(self):
        a=activity({'activityId':1,'activityName':'Synthetic','activityType':{'typeKey':'running'},'startTimeLocal':'2026-01-02T09:00:00','distance':5000,'duration':1500,'averageHR':140})
        self.assertEqual(a['pace'],300);self.assertEqual(a['date'],'2026-01-02');self.assertIsNone(a['cadence'])
        self.assertIsNone(num(-1));self.assertIsNone(num(float('nan')))
    def test_daily_v2_and_weight_kilograms(self):
        with tempfile.TemporaryDirectory() as p:
            s=Store(p)
            s.put('daily','a',{'data':[{'calendarDate':'2026-01-01','heartRate':{'restingValue':48},'movement':{'steps':{'value':9876}},'bodyBattery':{'latestValue':65}}]})
            s.put('hrv','a',{'hrvSummaries':[{'calendarDate':'2026-01-01','lastNightAvg':58}]})
            s.put('sleep','a',[{'calendarDate':'2026-01-01','sleepTimeSeconds':27000,'sleepScores':{'overall':{'value':88}}}])
            s.put('weight','a',{'dailyWeightSummaries':[{'summaryDate':'2026-01-01','latestWeight':{'weight':72.5}}]})
            d=health(s)[0];self.assertEqual(d['rhr'],48);self.assertEqual(d['weight'],72.5);self.assertEqual(d['sleepScore'],88)
            self.assertEqual(d['steps'],9876);self.assertEqual(d['hrv'],58);s.close()
    def test_production_empty(self):
        with tempfile.TemporaryDirectory() as p:
            s=Store(p);d=dashboard(s);self.assertEqual(d['activities'],[]);self.assertEqual(d['health'],[]);self.assertFalse(d['meta']['synthetic']);s.close()

if __name__=='__main__':unittest.main()
