"""Explicit test-only database builder, never loaded by production."""
import math
from pathlib import Path
import sqlite3
from datetime import date,timedelta
from companion.store import Store,now

def seed(directory):
    # Refuse to overwrite any existing non-fixture database, even with a test-like name.
    existing=Path(directory)/'dashboard.sqlite3'
    if existing.exists():
        db=sqlite3.connect(f'file:{existing}?mode=ro',uri=True)
        try:
            row=db.execute("SELECT value FROM metadata WHERE key='synthetic'").fetchone()
            if row is None or row[0]!='true':raise ValueError('Refusing to seed a non-fixture database')
        finally:db.close()
    s=Store(directory);s.meta('synthetic',True)
    today=date.today()
    for i in range(84):
        d=(today-timedelta(days=83-i)).isoformat()
        s.put('daily',d,{'data':[{'calendarDate':d,'heartRate':{'restingValue':49+round(3*math.sin(i/6))},'stress':{'avgLevel':29+round(7*math.sin(i/5))},'bodyBattery':{'latestValue':64+round(12*math.cos(i/9))},'movement':{'steps':{'value':8500+int(2400*math.sin(i))}},'respiration':{'avgValue':14},'pulseOx':{'avgValue':97}}]})
        s.put('sleep',d,[{'calendarDate':d,'sleepTimeSeconds':27000+int(1800*math.sin(i/4)),'sleepScores':{'overall':{'value':82+round(7*math.sin(i/4))}}}])
        s.put('hrv',d,{'hrvSummaries':[{'calendarDate':d,'lastNightAvg':58+round(8*math.sin(i/7))}]})
        if i%2==0:
            aid=str(1000+i);distance=15000 if i%14==0 else 5000 if i%10==0 else 7000+(i%5)*1000;speed=2.9+i/600;duration=distance/speed
            r={'activityId':int(aid),'activityName':['Morning easy run','Riverside steady run','Weekend long run'][i%3]+' · TEST','activityType':{'typeKey':'running'},'startTimeLocal':d+'T07:00:00','distance':distance,'duration':duration,'movingDuration':duration-10,'averageHR':152+i%3,'maxHR':162,'averageRunningCadenceInStepsPerMinute':174+i%4,'elevationGain':45+i%60,'calories':600,'fastestSplit_5000':5000/speed,**{'hrTimeInZone_'+str(j):duration*v for j,v in enumerate([.1,.6,.22,.06,.02],1)}}
            s.put('activities',aid,r)
            records=[{'t':t,'distance':min(t*speed,distance),'speed':speed+.04*math.sin(t/100),'hr':151+round(2*math.sin(t/200))+t/2000,'cadence':175+2*math.sin(t/100),'elevation':30+10*math.sin(t/300)} for t in range(0,int(duration),5)]
            records.append({'t':duration,'distance':distance,'speed':speed,'hr':153,'cadence':176,'elevation':30})
            s.put('series',aid,{'records':records,'laps':[]})
    s.meta('last_completed',now());s.meta('last_success',now());s.meta('history_start',(today-timedelta(days=83)).isoformat());s.meta('connection',{'state':'synthetic_test_only'});s.close()

if __name__=='__main__':
    import sys
    if len(sys.argv)!=2 or 'test' not in sys.argv[1].lower():raise SystemExit('Provide an explicitly named test directory.')
    seed(sys.argv[1])
