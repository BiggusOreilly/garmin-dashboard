"""Transparent metrics: no inferred Garmin health values or proprietary scores."""
from collections import defaultdict
from datetime import date,timedelta
from math import isfinite
from statistics import mean,pstdev
from .ingest import rows


def num(value):
    return float(value) if isinstance(value,(float,int)) and not isinstance(value,bool) and isfinite(value) and value>=0 else None

def avg(values):
    values=[v for v in values if v is not None]
    return mean(values) if values else None

def get(obj,*path):
    for k in path:
        if not isinstance(obj,dict):return None
        obj=obj.get(k)
    return num(obj)

def pace(distance,duration):
    return duration*1000/distance if distance and duration is not None and duration>0 else None

def activity(item,detail=None):
    d=detail if isinstance(detail,dict) else {};s=d.get('summaryDTO') if isinstance(d.get('summaryDTO'),dict) else item
    def field(a,b=None):return num(s.get(a)) if s.get(a) is not None else num(item.get(b or a))
    dist=field('distance');duration=field('duration')
    kind=d.get('activityTypeDTO') or item.get('activityType') or item.get('activityTypeDTO') or {}
    return {'id':str(item.get('activityId',d.get('activityId'))),'name':item.get('activityName') or d.get('activityName') or 'Untitled activity','date':str(s.get('startTimeLocal') or item.get('startTimeLocal') or '')[:10],'start':s.get('startTimeLocal') or item.get('startTimeLocal'),'type':kind.get('typeKey','unknown'),'distance':dist,'duration':duration,'elapsed':field('elapsedDuration'),'moving':field('movingDuration'),'pace':pace(dist,duration),'hr':field('averageHR') or None,'maxHR':field('maxHR') or None,'cadence':field('averageRunCadence','averageRunningCadenceInStepsPerMinute') or None,'elevation':field('elevationGain'),'stride':field('avgStrideLength','averageStrideLength'),'calories':field('calories'),'fiveK':num(item.get('fastestSplit_5000')) or None,'zones':[num(item.get('hrTimeInZone_'+str(i))) for i in range(1,6)],'trainingEffect':field('trainingEffect'),'recoveryTime':field('recoveryTime')}

def health(store):
    days={}
    def day(d):return days.setdefault(d,{'date':d})
    for payload in store.all('daily'):
        for x in rows(payload,('data',)):
            d=x.get('calendarDate')
            if not d:continue
            day(d).update({'rhr':get(x,'heartRate','restingValue'),'stress':get(x,'stress','avgLevel'),'bodyBattery':get(x,'bodyBattery','latestValue'),'bodyBatteryMax':get(x,'bodyBattery','maxValue'),'steps':get(x,'movement','steps','value'),'respiration':get(x,'respiration','avgValue'),'spo2':get(x,'pulseOx','avgValue'),'hydration':get(x,'hydration','consumedInFractionalMl')})
    for payload in store.all('sleep'):
        for x in rows(payload,('dailySleepDTOs','data','dailySleepSummaries')):
            d=x.get('calendarDate')
            if d:day(d).update({'sleep':num(x.get('sleepTimeSeconds')),'sleepScore':get(x,'sleepScores','overall','value')})
    for payload in store.all('hrv'):
        for x in rows(payload,('hrvSummaries','data')):
            d=x.get('calendarDate')
            if d:day(d).update({'hrv':num(x.get('lastNightAvg')),'hrvWeekly':num(x.get('weeklyAvg'))})
    for payload in store.all('weight'):
        for x in rows(payload,('dailyWeightSummaries',)):
            d=x.get('summaryDate');w=x.get('latestWeight') or {}
            if d:day(d).update({'weight':num(w.get('weight')),'bodyFat':num(w.get('bodyFat')),'bmi':num(w.get('bmi'))})
    return sorted(days.values(),key=lambda x:x['date'])

def intervals(records):
    from .quality import clean_intervals
    return [r for r in clean_intervals(records) if r['hr'] is not None]

def drift(records):
    """10-min warm-up removed, time-weighted speed/HR ratios over equal elapsed halves."""
    if not records:return {'value':None,'reason':'Requires recorded speed and heart rate for a continuous run.'}
    end=max((num(r.get('t')) or 0) for r in records)
    usable=intervals(records);usable=[r for r in usable if r['t']-r['dt']>=600]
    length=end-600
    if length<1200:return {'value':None,'reason':'Needs at least 20 minutes after a 10-minute warm-up.'}
    midpoint=600+length/2
    halves=[[],[]]
    for r in usable:
        begin=r['t']-r['dt'];stop=r['t']
        for i,(lo,hi) in enumerate([(600,midpoint),(midpoint,end)]):
            dt=max(0,min(stop,hi)-max(begin,lo))
            if dt:halves[i].append({**r,'dt':dt})
    ratios=[];speeds=[];hrs=[]
    for h in halves:
        seconds=sum(x['dt'] for x in h)
        if seconds<.8*(length/2):return {'value':None,'reason':'Insufficient continuous paired speed/HR coverage (80% per half required).'}
        speed=sum(x['speed']*x['dt'] for x in h)/seconds
        hr=sum(x['hr']*x['dt'] for x in h)/seconds
        speeds.append(speed);hrs.append(hr);ratios.append(speed/hr)
    all_speed=[r['speed'] for r in usable]
    if pstdev(all_speed)/mean(all_speed)>.15:return {'value':None,'reason':'Pace varies too much for a steady-run decoupling comparison (CV >15%).'}
    # Match common narrow bands in both halves instead of equating raw half means.
    matched_hr=[];matched_pace=[]
    from .quality import weighted
    for low in range(100,220,5):
        groups=[[r for r in h if low<=r['hr']<low+5] for h in halves]
        if all(sum(r['dt'] for r in g)>=120 for g in groups):
            matched_pace.append(1000/weighted(groups[1],'speed')-1000/weighted(groups[0],'speed'))
    for low in range(180,600,15):
        groups=[[r for r in h if low<=1000/r['speed']<low+15] for h in halves]
        if all(sum(r['dt'] for r in g)>=120 for g in groups):
            matched_hr.append(weighted(groups[1],'hr')-weighted(groups[0],'hr'))
    return {'value':100*(ratios[0]-ratios[1])/ratios[0],'hrAtPaceChange':avg(matched_hr),'paceAtHRChange':avg(matched_pace),'firstEfficiency':ratios[0],'secondEfficiency':ratios[1],'firstHR':hrs[0],'secondHR':hrs[1],'firstPace':1000/speeds[0],'secondPace':1000/speeds[1],'hrChange':100*(hrs[1]-hrs[0])/hrs[0],'paceChange':100*((1/speeds[1])/(1/speeds[0])-1),'reason':'Positive decoupling = lower speed per heartbeat in the second half. Terrain, heat, fatigue and sensor noise can affect it.'}

def kilometre_splits(records):
    """Interpolate cumulative distance crossings; do not mistake Garmin split summaries for km laps."""
    from .quality import number
    for a,b in zip(records,records[1:]):
        da,db,ta,tb=[number(v) for v in (a.get('distance'),b.get('distance'),a.get('t'),b.get('t'))]
        if None in (da,db,ta,tb):return []
        if tb<=ta or db<da or (db-da)/(tb-ta)>10:return []
    splits=[];previous=None;boundary=1000;last_time=None
    for r in records:
        d=num(r.get('distance'));t=num(r.get('t'))
        if d is None or t is None:continue
        if last_time is None:
            if d>100:return []
            last_time=t
        if previous:
            pd,pt=previous
            if d<pd:return []
            while d>=boundary and d>pd:
                crossing=pt+(t-pt)*(boundary-pd)/(d-pd)
                splits.append({'km':len(splits)+1,'pace':crossing-last_time,'duration':crossing-last_time})
                last_time=crossing;boundary+=1000
        previous=(d,t)
    from .quality import clean_intervals, weighted
    valid=clean_intervals(records)
    for s in splits:
        chunk=[r for r in valid if r['distance'] is not None and (s['km']-1)*1000<r['distance']<=s['km']*1000]
        s['hr']=weighted(chunk,'hr');s['cadence']=weighted(chunk,'cadence')
    return splits

def detail_metrics(series):
    records=(series or {}).get('records',[]);splits=kilometre_splits(records)
    p=[s['pace'] for s in splits]
    from .quality import clean_intervals, weighted
    valid=clean_intervals(records)
    mid=(records[-1]['t']/2) if records else 0
    def cad(h):return weighted([r for r in valid if (r['t']<mid)==h],'cadence')
    first=cad(True);second=cad(False)
    n=len(p)//2
    split_change=(avg(p[-n:])/avg(p[:n])-1)*100 if n and avg(p[:n]) else None
    return {'drift':drift(records),'splits':splits,'splitCV':pstdev(p)/mean(p)*100 if len(p)>1 and mean(p)>0 else None,'splitChange':split_change,'cadenceChange':second-first if first is not None and second is not None else None}

def dashboard(store):
    activities=sorted([activity(x,store.get('detail',str(x.get('activityId')))) for x in store.all('activities')],key=lambda x:x['date'],reverse=True)
    from .performance import derived, volume, progression, insights
    for run in activities:
        if 'running' in run['type']:
            run.update(derived(store,run))
            override=store.db.execute('SELECT classification FROM run_overrides WHERE id=?',(run['id'],)).fetchone()
            if override:
                run['classification']={**run['classification'],'label':override[0],'reason':'Your local manual override. Automatic: '+run['classification']['automatic'],'confidence':'manual'}
    days=health(store)
    runs=[r for r in activities if 'running' in r['type'] and r['date']]
    training=volume(runs)
    return {'training':training,'records':progression(runs),'insights':insights(runs,days,training,date.today().isoformat()),'activities':activities,'health':days,'meta':{'lastSuccess':store.meta('last_success'),'lastCompleted':store.meta('last_completed'),'lastAttempt':store.meta('last_attempt'),'earliest':store.meta('history_start'),'connection':store.meta('connection') or {'state':'not_connected'},'datasets':store.meta('datasets') or {},'warnings':store.meta('warnings') or [],'activityCount':len(activities),'healthDays':len(days),'synthetic':store.meta('synthetic') or False,'fitnessAge':get(store.get('fitnessAge','current'),'fitnessAge')},'units':'metric','gpsEnabled':False}
