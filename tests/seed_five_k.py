"""Isolated, clearly synthetic evidence-tier fixture. Never writes a production DB."""
from datetime import date,timedelta
from pathlib import Path
from companion.store import Store
from test_five_k import records

def seed(directory):
    directory=Path(directory)
    if 'test' not in str(directory).lower() or (directory/'dashboard.sqlite3').exists():raise ValueError('Use a new explicitly named test directory')
    s=Store(directory);s.meta('synthetic',True)
    samples=[('Sensor baseline',records(seconds=1792),1792),('Turnaround tolerated',records(seconds=1770,slowdown=4),1770),('Garmin summary PB',None,1609),('GPS teleport excluded',records(),1200),('Recording gap reported',records(),1700),('Distance reset excluded',records(),1500),('True stop excluded',records(slowdown=30),None)]
    for i,(name,rs,reported) in enumerate(samples):
        aid=str(9000+i);d=(date.today()-timedelta(days=14-i)).isoformat()
        if name.startswith('GPS teleport'):
            for r in rs:
                if r['t']>=900:r['distance']+=1000
        if name.startswith('Distance reset'):rs[900]['distance']=0
        if name.startswith('Recording gap'):
            for r in rs:
                if r['t']>=900:r['t']+=47
        item={'activityId':int(aid),'activityName':name+' · SYNTHETIC','startTimeLocal':d+'T08:00:00','activityType':{'typeKey':'running'},'distance':5000,'duration':1800,'fastestSplit_5000':reported}
        s.put('activities',aid,item)
        if rs:s.put('series',aid,{'records':rs,'laps':[]})
    s.close()
if __name__=='__main__':
    import sys
    seed(sys.argv[1])
