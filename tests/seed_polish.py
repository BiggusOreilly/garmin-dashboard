"""Realistic synthetic fixtures only. Never used during normal startup."""
from pathlib import Path
from seed_synthetic import seed
from test_records_extended import samples
from companion.store import Store

def build(directory):
    if 'test' not in str(directory).lower() or (Path(directory)/'dashboard.sqlite3').exists():raise ValueError('Use a new isolated test directory')
    seed(directory);s=Store(directory)
    cases=[('24971159968','2026-11-05T09:00:00','Turnaround 10K',10000,3570,samples(seconds=3570,slow=5),None,None),('24971159969','2026-10-12T07:00:00','Garmin 10K',10000,3600,None,None,3449.223456789),('24971159970','2026-10-22T08:00:00','Near 10K effort',9986,3600,None,None,None),('24971159971','2026-11-05T07:00:00','Earlier same-day run',5000,1609.344,None,1609.344,None),('24971159972','2026-11-07T07:00:00','Slower 10K',10000,3900,samples(seconds=3900),None,None)]
    for aid,start,name,distance,seconds,records,five,ten in cases:
        s.put('activities',aid,{'activityId':int(aid),'activityName':'SYNTHETIC '+name,'activityType':{'typeKey':'running'},'startTimeLocal':start,'distance':distance,'duration':seconds,'elapsedDuration':seconds+12.33,'movingDuration':seconds-4,'averageHR':154.378399,'maxHR':171,'averageRunningCadenceInStepsPerMinute':159.8274,'elevationGain':42.1234,'calories':700.32,'fastestSplit_5000':five,'fastestSplit_10000':ten})
        if records:s.put('series',aid,{'records':records,'laps':[]})
    s.close()
if __name__=='__main__':
    import sys
    build(sys.argv[1])
