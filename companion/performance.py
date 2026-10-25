"""Versioned local performance analysis. All fixtures and computations stay local."""
from bisect import bisect_left
from collections import defaultdict
from datetime import date, timedelta
from math import sqrt
from statistics import mean, pstdev
import json
from .quality import clean_intervals, weighted, report, number

VERSION = 6
DISTANCES = {'400 m':400, '1 km':1000, '1 mile':1609.344, '3 km':3000, '5 km':5000, '10 km':10000}
CLASSES = ['Recovery','Easy','Aerobic','Long','Steady','Tempo','Threshold','Intervals','VO2 / high intensity','Race / time trial','Mixed / unclassified']


def bands(records):
    """Remove warm-up and retain >=30s continuous paired movement in the same band."""
    valid = [r for r in clean_intervals(records) if r['t']-r['dt'] >= 600 and r['hr'] is not None]
    output = {}
    for mode, lows in [('hr', range(100,200,5)), ('pace', range(180,601,15))]:
        bins = defaultdict(list)
        for low in lows:
            high = low + (5 if mode == 'hr' else 15)
            chunks = []; chunk = []
            for r in valid:
                v = r['hr'] if mode == 'hr' else 1000/r['speed']
                if low <= v < high and (not chunk or r['t']-r['dt'] <= chunk[-1]['t']+.01):
                    chunk.append(r)
                else:
                    if sum(x['dt'] for x in chunk) >= 30: chunks.extend(chunk)
                    chunk = [r] if low <= v < high else []
            if sum(x['dt'] for x in chunk) >= 30: chunks.extend(chunk)
            seconds = sum(r['dt'] for r in chunks)
            if seconds >= 180:
                bins[str(low)] = {'value':1000/weighted(chunks,'speed') if mode == 'hr' else weighted(chunks,'hr'), 'seconds':seconds}
        output[mode] = dict(bins)
    return output


def segments(records):
    """O(targets*n log n), exact interpolated ends, elapsed time includes all pauses.
    Reject any gap, distance reset/spike, or >10s sampling inside a candidate.
    """
    rs = [r for r in records if number(r.get('t')) is not None and number(r.get('distance')) is not None]
    if len(rs) < 3: return {}
    ds = [r['distance'] for r in rs]; ts = [r['t'] for r in rs]
    if any(b < a for a,b in zip(ds,ds[1:])): return {}
    bad = [0]; valid_hrs=[None]; hr_sum=[0]; hr_secs=[0]; cad_sum=[0]; cad_secs=[0]
    maxgap = max((b-a for a,b in zip(ts,ts[1:])), default=0)
    for a,b in zip(rs,rs[1:]):
        dt = b['t']-a['t']; dd=b['distance']-a['distance']
        invalid = not (0 < dt <= 10 and .5 <= dd/dt <= 10)
        sp = number(b.get('speed'))
        invalid |= sp is not None and dt>0 and abs(dd/dt-sp)>max(1.5,sp*.5)
        bad.append(bad[-1]+int(invalid))
        hr=number(b.get('hr')); old=number(a.get('hr'))
        goodhr=hr is not None and 35<=hr<=220 and (old is None or dt>0 and abs(hr-old)/dt<=5)
        valid_hrs.append(hr if goodhr else None)
        cad=number(b.get('cadence')); goodcad=cad is not None and 80<=cad<=240
        hr_sum.append(hr_sum[-1]+(hr*dt if goodhr else 0)); hr_secs.append(hr_secs[-1]+(dt if goodhr else 0))
        cad_sum.append(cad_sum[-1]+(cad*dt if goodcad else 0)); cad_secs.append(cad_secs[-1]+(dt if goodcad else 0))
    output={}
    for label, length in DISTANCES.items():
        # 400m needs <=2s recording; smart-recorded short segments are omitted.
        if length==400 and maxgap>2: continue
        best=None
        for i,a in enumerate(rs[:-1]):
            target=ds[i]+length
            j=bisect_left(ds,target,i+1)
            if j>=len(rs):break
            if bad[j]-bad[i] or ds[j]==ds[j-1]:continue
            fraction=(target-ds[j-1])/(ds[j]-ds[j-1])
            finish=ts[j-1]+fraction*(ts[j]-ts[j-1]); seconds=finish-ts[i]
            ea,eb=number(a.get('elevation')),number(rs[j].get('elevation'))
            descent=(eb-ea)/length if ea is not None and eb is not None else None
            # Keep flagged downhill performances visible, never equate them with records.
            flagged=descent is not None and descent < -.01
            if best is not None and (flagged,seconds)>=(bool(best['flag']),best['seconds']):continue
            def sensor(total,coverage):
                dt=(ts[j]-ts[j-1])*(1-fraction)
                covered=coverage[j]-coverage[i]-(dt if coverage[j]>coverage[j-1] else 0)
                value=total[j]-total[i]-(dt*(total[j]-total[j-1])/(ts[j]-ts[j-1]) if ts[j]>ts[j-1] else 0)
                return value/covered if covered>=seconds*.8 and covered else None
            def crossing(d):
                k=bisect_left(ds,d,i+1)
                return ts[k-1]+(ts[k]-ts[k-1])*(d-ds[k-1])/(ds[k]-ds[k-1])
            splits=[];prev=ts[i]
            for km in range(1,int(length//1000)+1):
                t=crossing(ds[i]+km*1000);splits.append(t-prev);prev=t
            half=crossing(ds[i]+length/2)-ts[i]
            best={'seconds':seconds,'start':ts[i],'end':finish,'hr':sensor(hr_sum,hr_secs),'cadence':sensor(cad_sum,cad_secs),
                  'maxHR':max((h for h in valid_hrs[i+1:j+1] if h is not None),default=None),
                  'splits':splits,'splitCV':100*pstdev(splits)/mean(splits) if len(splits)>1 else None,
                  'halfChange':100*((seconds-half)/half-1) if half else None,'finalKm':splits[-1] if splits else None,
                  'flag':'Downhill >1% net descent' if flagged else None,'terrain':'Elevation available' if descent is not None else 'Elevation unavailable; grade unverified',
                  'precision':f'Interpolated; up to {maxgap:g}s sampling'}
        if best:output[label]=best
    return output


def classify(run, records):
    rs=clean_intervals(records); hrs=[r for r in rs if r['hr'] is not None]
    seconds=sum(r['dt'] for r in rs); zones=run.get('zones') or []
    total=sum(v or 0 for v in zones); high=sum((zones[i] or 0) for i in (3,4)) / total if total and len(zones)==5 else None
    moderate=(zones[2] or 0)/total if total and len(zones)==5 else None
    speeds=[r['speed'] for r in rs]; cv=pstdev(speeds)/mean(speeds) if len(speeds)>1 else None
    confidence='provisional'; label='Mixed / unclassified'; reason='Insufficient zone or sensor evidence; pace alone is not a classification.'
    name=run['name'].lower()
    if any(word in name for word in ('race','time trial','parkrun')):
        label='Race / time trial';reason='Activity title indicates a race or time trial; this is a label cue, not verification.'
    elif seconds>=600 and cv is not None and cv>.18 and len(hrs)>.8*len(rs):
        # Require repeated changes at 30s resolution, not individual GPS noise.
        buckets=defaultdict(list)
        for r in rs:buckets[int(r['t']//30)].append(r['speed'])
        means=[mean(v) for _,v in sorted(buckets.items())];baseline=mean(means)
        crossings=sum((a>baseline*1.1)!=(b>baseline*1.1) for a,b in zip(means,means[1:]))
        if crossings>=6:label='Intervals';reason=f'{crossings} sustained changes across 30-second speed blocks with paired HR; interval-like structure.'
    if label=='Mixed / unclassified' and high is not None:
        confidence='moderate'
        if (zones[4] or 0)/total>.35:label='VO2 / high intensity';reason='Over 35% of recorded zone time in Garmin zone 5; physiological VO2 work is unverified.'
        elif high>.65:label='Threshold';reason='Over 65% of recorded zone time in Garmin zones 4–5; depends on your zone configuration.'
        elif high>.35:label='Tempo';reason='Over 35% of recorded zone time in Garmin zones 4–5.'
        elif (run.get('duration') or 0)>=4500:label='Long';reason='At least 75 minutes, with at most 35% of zone time in zones 4–5.'
        elif moderate is not None and moderate>.5:label='Steady';reason='More than half of recorded zone time in Garmin zone 3.'
        elif (zones[0] or 0)/total>.6 and (run.get('duration') or 0)<2700:label='Recovery';reason='Shorter than 45 minutes with >60% of zone time in zone 1.'
        elif sum(v or 0 for v in zones[:2])/total>.8:label='Easy';reason='More than 80% of recorded zone time in Garmin zones 1–2.'
        else:label='Aerobic';reason='Predominantly Garmin zones 1–3 without sustained high-zone dominance.'
    return {'label':label,'reason':reason,'confidence':confidence,'automatic':label}


def derived(store, run):
    aid=run['id']
    stamps=list(store.db.execute("SELECT dataset,fetched FROM records WHERE id=? AND dataset IN ('series','activities','detail') ORDER BY dataset",(aid,)))
    fingerprint=json.dumps([VERSION,stamps])
    row=store.db.execute('SELECT payload FROM derived_runs WHERE id=? AND fingerprint=?',(aid,fingerprint)).fetchone()
    if row:return json.loads(row[0])
    from .analysis import detail_metrics
    records=(store.get('series',aid) or {}).get('records',[])
    result={'metrics':detail_metrics({'records':records}),'bands':bands(records),'records':segments(records),'quality':report(records),'classification':classify(run,records)}
    recorded_distance=max((number(r.get('distance')) or 0 for r in records),default=0)
    if records and run.get('distance') and recorded_distance<run['distance']*.95:
        result['quality']['issues'].append('Incomplete sensor recording: less than 95% of summary distance')
        result['quality']['status']='review'
    store.db.execute('INSERT OR REPLACE INTO derived_runs VALUES(?,?,?)',(aid,fingerprint,json.dumps(result,allow_nan=False)));store.db.commit()
    return result


def similar(run, runs):
    result=[]
    for r in runs:
        if r['id']==run['id'] or r['date']>run['date']:continue
        if not run.get('distance') or not r.get('distance') or not run.get('duration') or not r.get('duration'):continue
        dd=abs(r['distance']/run['distance']-1);dt=abs(r['duration']/run['duration']-1)
        if dd>.25 or dt>.35:continue
        score=dd*3+dt
        for key,scale in [('hr',20),('pace',90),('elevation',100)]:
            if r.get(key) is not None and run.get(key) is not None:score+=abs(r[key]-run[key])/scale*.2
        if r.get('classification',{}).get('label')!=run.get('classification',{}).get('label'):score+=.25
        eff=lambda x:1000/x['pace']/x['hr'] if x.get('pace') and x.get('hr') else None
        a,b=eff(run),eff(r);delta=100*(a/b-1) if a and b else None
        result.append({'id':r['id'],'score':round(score,3),'efficiencyChange':delta,
                       'assessment':'Insufficient reliable data' if delta is None else 'Better' if delta>2 else 'Worse' if delta<-2 else 'Similar'})
    return sorted(result,key=lambda x:x['score'])[:5]


def volume(runs, end=None):
    if not runs:return {'daily':[],'weekly':[],'monthly':[]}
    end=end or date.today().isoformat(); byday=defaultdict(list)
    for r in runs:
        if r.get('date') and r['date']<=end:byday[r['date']].append(r)
    if not byday:return {'daily':[],'weekly':[],'monthly':[]}
    start=date.fromisoformat(min(byday)); stop=date.fromisoformat(end); daily=[]; weeks={}; months={}
    rolling7=rolling28=0; kms=[]
    for i in range((stop-start).days+1):
        d=start+timedelta(days=i); key=d.isoformat(); rs=byday[key]; km=sum(r.get('distance') or 0 for r in rs)/1000;kms.append(km)
        rolling7+=km-(kms[i-7] if i>=7 else 0);rolling28+=km-(kms[i-28] if i>=28 else 0)
        daily.append({'date':key,'km':km,'rolling7':rolling7,'rolling28':rolling28,'count':len(rs)})
        wk=(d-timedelta(days=d.weekday())).isoformat();mo=key[:7]+'-01'
        for mapping,k in [(weeks,wk),(months,mo)]:
            x=mapping.setdefault(k,{'date':k,'km':0,'count':0,'longest':0,'zoneMinutes':0})
            x['km']+=km;x['count']+=len(rs);x['longest']=max([x['longest']]+[(r.get('distance') or 0)/1000 for r in rs])
            x['zoneMinutes']+=sum(sum((v or 0)*(j+1) for j,v in enumerate(r.get('zones',[])))/60 for r in rs)
    weekly=list(weeks.values())
    for i,w in enumerate(weekly):
        previous=weekly[i-1]['km'] if i else None; baseline=mean([x['km'] for x in weekly[i-4:i]]) if i>=4 else None
        w.update(average=w['km']/w['count'] if w['count'] else None,longShare=100*w['longest']/w['km'] if w['km'] else None,
                 change=100*(w['km']/previous-1) if previous else None,baseline=baseline,
                 abrupt=bool(baseline and w['km']>baseline*1.3 and w['km']-baseline>=5),
                 complete=w['date'] <= (date.fromisoformat(end)-timedelta(days=6)).isoformat())
    return {'daily':daily,'weekly':weekly,'monthly':list(months.values())}


def progression(runs):
    output={}
    for label in DISTANCES:
        events=[];best=None
        for r in sorted(runs,key=lambda x:(x['date'],x['id'])):
            p=r.get('records',{}).get(label)
            if not p or p.get('flag'):continue
            if best is None or p['seconds']<best:
                events.append({**p,'id':r['id'],'date':r['date'],'name':r['name'],'improvement':best-p['seconds'] if best else None})
                best=p['seconds']
        output[label]=events
    longest=[]; best=0
    for r in sorted(runs,key=lambda x:(x['date'],x['id'])):
        if (r.get('distance') or 0)>best:
            longest.append({'id':r['id'],'date':r['date'],'name':r['name'],'distance':r['distance'],'hr':r.get('hr'),'improvement':r['distance']-best if best else None});best=r['distance']
    output['Longest run']=longest
    return output


def correlation(points):
    n=len(points)
    if n<10:return {'n':n,'r':None,'reason':'Insufficient reliable data: at least 10 paired days required.'}
    xs,ys=zip(*points);mx,my=mean(xs),mean(ys)
    xx=sum((x-mx)**2 for x in xs);yy=sum((y-my)**2 for y in ys)
    r=sum((x-mx)*(y-my) for x,y in points)/sqrt(xx*yy) if xx and yy else None
    return {'n':n,'r':r,'reason':'Association only. Weather, terrain, intensity and repeated observations can confound this relationship.'}


def trend(points, end, window=28):
    end=date.fromisoformat(end);cut=(end-timedelta(days=window-1)).isoformat();prior=(end-timedelta(days=2*window-1)).isoformat()
    recent=[x['value'] for x in points if cut<=x['date']<=end.isoformat()];old=[x['value'] for x in points if prior<=x['date']<cut]
    return {'recentN':len(recent),'previousN':len(old),'change':mean(recent)-mean(old) if min(len(recent),len(old))>=3 else None,
            'recent':mean(recent) if len(recent)>=3 else None,'best':min(recent) if len(recent)>=3 else None}


def insights(runs, days, volumes, end):
    out=[]
    def add(key,text,why,page,rank):out.append({'id':key,'text':text,'evidence':why,'page':page,'rank':rank})
    for low in (140,145,150,155,160):
        pts=[{'date':r['date'],'value':r['bands']['hr'][str(low)]['value']} for r in runs if str(low) in r.get('bands',{}).get('hr',{})]
        t=trend(pts,end)
        if t['change'] is not None and abs(t['change'])>=5:
            add('aerobic'+str(low),f"Pace at {low}–{low+5} bpm was {abs(t['change']):.0f} sec/km {'faster' if t['change']<0 else 'slower'} in the last 4 weeks.",f"{t['recentN']} recent and {t['previousN']} previous runs; ≥3 minutes of stable matching samples each. Terrain and weather are not adjusted.",'Aerobic Efficiency',95)
            break
    ws=volumes['weekly']
    complete=[w for w in ws if w['complete']]
    if complete and complete[-1]['abrupt']:
        w=complete[-1];add('volume',f"Last complete week’s volume was {100*(w['km']/w['baseline']-1):.0f}% above the previous 4-week average.",f"{w['km']:.1f} km vs {w['baseline']:.1f} km; descriptive flag (>30% and ≥5 km), not an injury prediction.",'Training Load',90)
    recent_days=[d for d in days if d['date']<=end]
    if len(recent_days)>=24:
        last=recent_days[-3:];baseline_start=(date.fromisoformat(last[0]['date'])-timedelta(days=28)).isoformat()
        base=[d['rhr'] for d in recent_days if baseline_start<=d['date']<last[0]['date'] and d.get('rhr') is not None]
        if len(base)>=21 and all(d.get('rhr') is not None and d['rhr']>=mean(base)+5 for d in last) and (date.fromisoformat(last[-1]['date'])-date.fromisoformat(last[0]['date'])).days==2:
            add('rhr','Resting HR has been at least 5 bpm above its preceding baseline for three recorded days.',f'{len(base)} baseline days; mean {mean(base):.1f} bpm. No medical interpretation.','Recovery',85)
    pb=progression(runs)['5 km']
    cutoff=(date.fromisoformat(end)-timedelta(weeks=12)).isoformat();recent=[p for p in pb if p['date']>=cutoff]
    if len(recent)>=2 and recent[0]['seconds']-recent[-1]['seconds']>=5:
        add('pb',f"Your recorded 5 km best improved by {recent[0]['seconds']-recent[-1]['seconds']:.0f} seconds within the last 12 weeks.",f'{len(recent)} PB events from reliable, unflagged segments. Imported history only.','5K Performance',100)
    cutoff=(date.fromisoformat(end)-timedelta(days=83)).isoformat()
    steady=[r for r in runs if r['date']>=cutoff and r.get('classification',{}).get('label') in ('Easy','Aerobic','Long','Steady')]
    drift_points=[{'date':r['date'],'value':r['metrics']['drift']['value']} for r in steady if r.get('metrics',{}).get('drift',{}).get('value') is not None]
    t=trend(drift_points,end)
    if t['change'] is not None and abs(t['change'])>=1.5:
        add('drift',f"Steady-run decoupling was {abs(t['change']):.1f} percentage points {'lower' if t['change']<0 else 'higher'} in the last 4 weeks.",f"{t['recentN']} recent vs {t['previousN']} prior steady runs passing coverage and variability checks. Conditions may differ.",'Fitness Trends',80)
    ordered=sorted(steady,key=lambda r:r['date'])
    if ordered:
        anchor=ordered[-1]
        comparable=[r for r in ordered if r.get('distance') and anchor.get('distance') and abs(r['distance']/anchor['distance']-1)<=.15 and r.get('hr') and anchor.get('hr') and abs(r['hr']-anchor['hr'])<=3 and r.get('pace') and (r.get('duration') or 0)>=1200][-3:]
        if len(comparable)==3 and all(a['pace']-b['pace']>=5 for a,b in zip(comparable,comparable[1:])):
            add('comparable','Your last three comparable steady runs were progressively faster at similar average HR.',f"Distance ±15%, HR ±3 bpm: pace {', '.join(str(round(r['pace'])) for r in comparable)} sec/km; HR {', '.join(str(round(r['hr'])) for r in comparable)} bpm. Summary-level association, not terrain-adjusted.",'Run Comparison',88)
    rec=recovery_analysis(runs,days,volumes,'sleep','performance',1)['points']
    short=[p['performance'] for p in rec if p.get('x') is not None and p['x']<6.5 and p['performance'] is not None]
    rested=[p['performance'] for p in rec if p.get('x') is not None and p['x']>=7 and p['performance'] is not None]
    if min(len(short),len(rested))>=5 and abs(mean(short)-mean(rested))>=3:
        delta=mean(short)-mean(rested)
        add('sleep',f"Runs after under 6.5 hours of prior-day sleep were associated with {abs(delta):.1f} bpm {'higher' if delta>0 else 'lower'} HR at comparable pace.",f"{len(short)} short-sleep vs {len(rested)} ≥7-hour nights; HR at 5:30–5:45/km. Unadjusted association; no causation implied.",'Recovery',75)
    return sorted(out,key=lambda x:-x['rank'])[:12]


def recovery_analysis(runs, days, training, metric='hrv', against='performance', lag=1):
    """One observation per calendar day; paired relationships use fixed pace band."""
    daymap={d['date']:d for d in days};vol={d['date']:d for d in training.get('daily',[])};bydate=defaultdict(list)
    for r in runs:
        b=r.get('bands',{}).get('pace',{}).get('330')
        if b:bydate[r['date']].append((r['id'],b['value']))
    out=[]
    for d in days:
        source=daymap.get((date.fromisoformat(d['date'])-timedelta(days=lag)).isoformat(),{})
        x=source.get(metric);x=x/3600 if x is not None and metric=='sleep' else x
        rs=bydate[d['date']];previous=(date.fromisoformat(d['date'])-timedelta(days=1)).isoformat()
        out.append({**d,'sleep':d['sleep']/3600 if d.get('sleep') is not None else None,'x':x,
                    'performance':mean([v for _,v in rs]) if rs else None,'id':rs[0][0] if rs else None,
                    'volume':vol.get(d['date'],{}).get('rolling7'),'previousTraining':vol.get(previous,{}).get('km')})
    paired=[(p['x'],p[against]) for p in out if p['x'] is not None and p[against] is not None]
    return {'points':out,'association':correlation(paired)}
