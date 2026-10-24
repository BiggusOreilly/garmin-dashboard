"""Resumable, bounded official API ingestion. No live credentials needed on Cloud."""
from datetime import date, timedelta
from contextlib import contextmanager
import json
import os
import time
from .garmin import Garmin, SafeError
from .fit import parse_fit
from .store import Store, now

DATASETS={
 'daily':('get_daily_summaries',28), 'sleep':('get_daily_sleep_summaries',28),
 'hrv':('get_daily_hrv_summaries',28),'bodyBattery':('get_daily_body_battery',28),
 'stress':('get_daily_stress',28),'steps':('get_daily_steps',28),
 'hydration':('get_daily_hydration',28),'weight':('get_weight_measurements',28),
 'wellnessActivities':('get_wellness_activity_summaries',28),
}

def windows(start,end,days=28):
    while start<=end:
        stop=min(start+timedelta(days=days-1),end)
        yield start.isoformat(),stop.isoformat()
        start=stop+timedelta(days=1)

@contextmanager
def sync_lock(directory):
    import fcntl
    path=directory/'sync.lock'
    with open(path,'a') as handle:
        os.chmod(path,0o600)
        try: fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise SafeError('A refresh is already running. Please wait for it to finish.') from None
        try: yield
        finally: fcntl.flock(handle,fcntl.LOCK_UN)

def strip_location(value):
    if isinstance(value,dict):
        return {k:strip_location(v) for k,v in value.items() if not any(s in k.lower() for s in ('latitude','longitude','position_lat','position_long','locationname','polyline','gps'))}
    if isinstance(value,list):return [strip_location(v) for v in value]
    return value

def rows(value,keys=()):
    if isinstance(value,list):return [v for v in value if isinstance(v,dict)]
    if isinstance(value,dict):
        for k in keys:
            if isinstance(value.get(k),list):return rows(value[k])
    return []

def validate_payload(dataset,payload):
    """Allow added fields, reject incompatible top-level contracts without losing old cache."""
    if payload is None:return
    required={'daily':'data','hrv':'hrvSummaries','weight':'dailyWeightSummaries'}
    if dataset in required:
        valid=isinstance(payload,dict) and isinstance(payload.get(required[dataset]),list)
    else:
        valid=isinstance(payload,list)
    if not valid:
        raise SafeError('Garmin returned an unexpected '+dataset+' response shape. Existing cached data was kept; this dataset needs review.')


def range_fetch(api,method,start,end):
    """Split further if Garmin changes a documented range limit."""
    try:return [(start,end,api.call(method,start,end))]
    except SafeError as e:
        a=date.fromisoformat(start);b=date.fromisoformat(end)
        if e.status==400 and a<b:
            mid=a+(b-a)//2
            return range_fetch(api,method,start,mid.isoformat())+range_fetch(api,method,(mid+timedelta(days=1)).isoformat(),end)
        raise

def refresh(store,api=None,today=None,history_start=None):
    today=today or date.today()
    own=api is None
    warnings=[]
    with sync_lock(store.directory):
        try:
            store.meta('last_attempt',now())
            api=api or Garmin()
            store.meta('connection',{'state':'connected','checked':now()})
            last=store.meta('activities_through')
            start=(date.fromisoformat(last)-timedelta(days=14)).isoformat() if last else None
            offset=0;seen=set();activity_ids=[]
            while True:
                page=api.call('search_activities',start=offset,limit=99,start_date=start,end_date=today.isoformat())
                if not isinstance(page,list):raise SafeError('Garmin returned an unexpected activity list. Existing data is safe; the refresh was not marked complete.')
                if not page:break
                ids=[str(x['activityId']) for x in page if isinstance(x,dict) and x.get('activityId')]
                if not ids or all(i in seen for i in ids):raise SafeError('Garmin repeated an activity page. Refresh stopped safely; please try again later.')
                for item in page:
                    if not isinstance(item,dict) or not item.get('activityId'):continue
                    aid=str(item['activityId']);seen.add(aid);activity_ids.append(aid)
                    store.put('activities',aid,strip_location(item))
                offset+=len(page)
                # A short page can be a server cap; continue until an empty page.
            store.meta('activities_through',today.isoformat())
            # Retry previously failed details/FIT on each sync as well.
            for aid,item in store.items('activities'):
                if aid in activity_ids or store.get('detail',aid) is None:
                    try:store.put('detail',aid,strip_location(api.call('get_activity',aid)))
                    except SafeError as e:warnings.append('Activity details: '+str(e))
                typ=(item.get('activityType') or item.get('activityTypeDTO') or {}).get('typeKey','')
                if 'running' in typ and (aid in activity_ids or store.get('series',aid) is None):
                    try:
                        blob=api.call('download_activity',aid)
                        # Keep original only on Mac, behind 0700 directory; it may contain GPS.
                        folder=store.directory/'fit';folder.mkdir(exist_ok=True,mode=0o700)
                        path=folder/(aid+'.zip');path.write_bytes(blob);path.chmod(0o600)
                        store.put('series',aid,parse_fit(blob))
                    except SafeError as e:warnings.append('Activity FIT: '+str(e))
                    except Exception:warnings.append('An activity file could not be decoded. Summary data remains available.')
            dates=[str(x.get('startTimeLocal',''))[:10] for x in store.all('activities') if x.get('startTimeLocal')]
            earliest=history_start or (date.fromisoformat(min(dates)) if dates else today-timedelta(days=364))
            previous_start=store.meta('history_start')
            if previous_start and history_start is None:earliest=min(earliest,date.fromisoformat(previous_start))
            store.meta('history_start',earliest.isoformat())
            status=store.meta('datasets') or {}
            for dataset,(method,days) in DATASETS.items():
                cursor=store.meta('cursor:'+dataset)
                first=max(earliest,date.fromisoformat(cursor)-timedelta(days=14)) if cursor else earliest
                complete=True;count=0
                for a,b in windows(first,today,days):
                    try:
                        chunks=range_fetch(api,method,a,b)
                        for x,y,payload in chunks:
                            validate_payload(dataset,payload)
                            store.put(dataset,x+':'+y,strip_location(payload));count+=1
                        # Cursor progresses only across contiguous successful windows.
                        if complete:store.meta('cursor:'+dataset,b)
                    except SafeError as e:
                        complete=False;warnings.append(dataset+': '+str(e))
                        if e.status in (401,403,429):break
                status[dataset]={'state':'checked' if complete else 'partial','checked':now(),'windows':count}
                store.meta('datasets',status)
            # Daily endpoints, including raw daily HR/SpO2, fetched in resumable single-day windows.
            for dataset,method in [('dailyHeartRate','get_daily_heart_rate'),('spo2','get_daily_spo2')]:
                cursor=store.meta('cursor:'+dataset)
                first=max(earliest,date.fromisoformat(cursor)-timedelta(days=2)) if cursor else earliest
                complete=True
                for a,b in windows(first,today,1):
                    try:
                        store.put(dataset,a,strip_location(api.call(method,a)))
                        if complete:store.meta('cursor:'+dataset,b)
                    except SafeError as e:
                        complete=False;warnings.append(dataset+': '+str(e))
                        if e.status in (401,403,429):break
                status[dataset]={'state':'checked' if complete else 'partial','checked':now()}
            for dataset,method,args in [('zones','get_heart_rate_zones',()),('fitnessAge','get_fitness_age',(today.isoformat(),))]:
                try:
                    store.put(dataset,'current',strip_location(api.call(method,*args)))
                    status[dataset]={'state':'checked','checked':now()}
                except SafeError as e:
                    warnings.append(dataset+': '+str(e));status[dataset]={'state':'partial','checked':now()}
            store.meta('datasets',status)
            store.meta('last_attempt',now());store.meta('warnings',sorted(set(warnings)))
            if not warnings:store.meta('last_success',now())
            store.meta('last_completed',now())
            return {'activities':len(store.all('activities')),'warnings':len(set(warnings))}
        except SafeError as e:
            store.meta('connection',{'state':'error','message':str(e),'checked':now()});raise
        finally:
            if own and api:api.close()
