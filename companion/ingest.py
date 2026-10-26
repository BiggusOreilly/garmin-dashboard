"""Resumable, bounded official API ingestion. No live credentials needed on Cloud."""
from datetime import date, timedelta, datetime, timezone
from contextlib import contextmanager
import json
import hashlib
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

def refresh(store,api=None,today=None,history_start=None,progress=None,revalidate_all=False):
    progress=progress or (lambda message:None)
    today=today or date.today()
    own=api is None
    warnings=[]
    with sync_lock(store.directory):
        try:
            store.meta('last_attempt',now())
            progress('Connecting securely to Garmin…')
            api=api or Garmin()
            store.meta('connection',{'state':'connected','checked':now()})
            last=store.meta('activities_through')
            start=(date.fromisoformat(last)-timedelta(days=14)).isoformat() if last else None
            offset=0;seen=set();activity_ids=[]
            while True:
                progress('Reading activity history, page '+str(offset//99+1)+'…')
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
            for index,(aid,item) in enumerate(store.items('activities'),1):
                if index==1 or index%20==0:progress('Checking activity details and running FIT files: '+str(index)+'…')
                if aid in activity_ids or store.get('detail',aid) is None:
                    try:store.put('detail',aid,strip_location(api.call('get_activity',aid)))
                    except SafeError as e:warnings.append('Activity details: '+str(e))
                typ=(item.get('activityType') or item.get('activityTypeDTO') or {}).get('typeKey','')
                if 'running' in typ and fit_retry_due(store,aid,item,force=revalidate_all):
                    try:import_activity_fit(store,api,aid,item,force_download=revalidate_all)
                    except SafeError as e:warnings.append('Activity FIT: '+str(e))
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
                for index,(a,b) in enumerate(windows(first,today,days),1):
                    progress('Importing '+dataset+' · window '+str(index)+'…')
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
                for index,(a,b) in enumerate(windows(first,today,1),1):
                    if index==1 or index%30==0:progress('Importing '+dataset+' · day '+str(index)+'…')
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


def fit_source(item):
    return hashlib.sha256(json.dumps(strip_location(item),sort_keys=True).encode()).hexdigest()


def fit_retry_due(store, aid, item, force=False, current=None):
    from .quality import series_retry_reason
    if force:return True
    status=store.meta('fit:'+aid) or {}
    changed=status.get('source') is not None and status['source']!=fit_source(item)
    if changed:return True
    problem=series_retry_reason(store.get('series',aid),item)
    if not problem and status.get('state')!='retry':
        if not status:store.meta('fit:'+aid,{'state':'usable','source':fit_source(item),'attempts':0})
        return False
    due=status.get('nextRetry')
    return not due or (current or datetime.now(timezone.utc))>=datetime.fromisoformat(due)


def import_activity_fit(store, api, aid, item, force_download=False):
    """Try existing local original first, then official download; retain better cache on failure."""
    from .quality import series_retry_reason
    if not str(aid).isdecimal():raise SafeError('Invalid activity identifier.')
    previous=store.get('series',aid);old=store.meta('fit:'+aid) or {}
    attempts=old.get('attempts',0)+1
    stamp=datetime.now(timezone.utc)
    status={'attempted':stamp.isoformat(),'source':fit_source(item),'attempts':attempts}
    path=store.directory/'fit'/(aid+'.zip')
    try:
        parsed=None;blob=None
        changed=old.get('source') is not None and old['source']!=fit_source(item)
        if path.is_file() and not force_download and not changed:
            try:parsed=parse_fit(path.read_bytes())
            except Exception:parsed=None
        if parsed is None or series_retry_reason(parsed,item):
            blob=api.call('download_activity',aid)
            try:parsed=parse_fit(blob)
            except Exception:raise SafeError('The original FIT could not be parsed. Existing cached data was kept.') from None
        if not isinstance(parsed,dict):raise SafeError('The original FIT could not be parsed. Existing cached data was kept.')
        def coverage(s):
            from .quality import number
            return max((number(r.get('distance')) or 0 for r in (s or {}).get('records',[])),default=0)
        # Never replace an existing better stream with an empty/truncated response.
        new_problem=series_retry_reason(parsed,item)
        keep_previous=previous is not None and new_problem is not None and (series_retry_reason(previous,item) is None or coverage(previous)>coverage(parsed))
        chosen=previous if keep_previous else parsed
        if not keep_previous:
            store.put('series',aid,parsed)
            if blob is not None:
                path.parent.mkdir(exist_ok=True,mode=0o700)
                temporary=path.with_name(aid+'.tmp.zip');temporary.write_bytes(blob);temporary.chmod(0o600);temporary.replace(path)
        reason=new_problem if keep_previous else series_retry_reason(chosen,item)
        status.update(state='retry' if reason else 'usable',reason=reason)
    except SafeError:
        status.update(state='retry',reason='FIT download or parsing failed; existing cache retained')
        status['nextRetry']=(stamp+timedelta(days=min(30,2**min(attempts-1,5)))).isoformat()
        store.meta('fit:'+aid,status)
        raise
    if status['state']=='retry':status['nextRetry']=(stamp+timedelta(days=min(30,2**min(attempts-1,5)))).isoformat()
    else:status['attempts']=0
    store.meta('fit:'+aid,status)
    if status['state']=='retry':raise SafeError('FIT remains incomplete or unavailable. Summary results are preserved; automatic retry is scheduled.')
    return status


def revalidate_activity(store, aid, api=None):
    if store.meta('synthetic'):raise SafeError('Synthetic fixture databases cannot connect to Garmin.')
    item=store.get('activities',aid)
    typ=(item or {}).get('activityType') or (item or {}).get('activityTypeDTO') or {}
    if item is None or 'running' not in typ.get('typeKey',''):raise SafeError('Running activity not found.')
    own=api is None
    with sync_lock(store.directory):
        try:
            api=api or Garmin()
            return import_activity_fit(store,api,aid,item,force_download=True)
        finally:
            if own and api:api.close()
