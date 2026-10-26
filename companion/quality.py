"""Shared coordinate-free sensor quality gates. Never interpolate across pauses."""
from math import isfinite


def number(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and isfinite(v) else None


def clean_intervals(records):
    out = []
    for a, b in zip(records, records[1:]):
        t, end = number(a.get('t')), number(b.get('t'))
        if t is None or end is None or not 0 < end-t <= 10:
            continue
        dt = end-t
        speed = number(b.get('speed'))
        if speed is None or not .5 <= speed <= 10:
            continue
        da, db = number(a.get('distance')), number(b.get('distance'))
        if da is not None and db is not None:
            measured = (db-da)/dt
            if measured < .5 or measured > 10 or abs(measured-speed) > max(1.5, speed*.5):
                continue
        hr = number(b.get('hr'))
        old = number(a.get('hr'))
        if hr is None or not 35 <= hr <= 220 or (old is not None and abs(hr-old)/dt > 5):
            hr = None
        cad = number(b.get('cadence'))
        if cad is None or not 80 <= cad <= 240:
            cad = None
        out.append({'t':end, 'dt':dt, 'speed':speed, 'hr':hr, 'cadence':cad,
                    'distance':db, 'elevation':number(b.get('elevation'))})
    return out


def weighted(rows, field):
    rs = [r for r in rows if r.get(field) is not None]
    seconds = sum(r['dt'] for r in rs)
    return sum(r[field]*r['dt'] for r in rs)/seconds if seconds else None


def report(records):
    good = clean_intervals(records)
    elapsed = max((number(r.get('t')) or 0 for r in records), default=0)
    covered = sum(r['dt'] for r in good)
    paired = sum(r['dt'] for r in good if r['hr'] is not None)
    issues = []
    if elapsed < 600: issues.append('Short recording: under 10 minutes')
    if not covered or covered < elapsed*.8: issues.append('Pauses, gaps or questionable movement reduce reliable coverage')
    if not paired or paired < covered*.8: issues.append('Missing or questionable heart rate')
    if not any(r['cadence'] is not None for r in good): issues.append('Cadence unavailable')
    return {'seconds':covered, 'hrSeconds':paired, 'coverage':covered/elapsed if elapsed else 0,
            'issues':issues, 'status':'review' if issues else 'usable'}


def chart_series(series, limit=2400):
    """Explicit projection and bounded display sampling; analyses use full originals."""
    records=series.get('records',[])
    clean={r['t']:r for r in clean_intervals(records)}
    step=max(1,(len(records)+limit-1)//limit)
    projected=[]
    for i in sorted(set(range(0,len(records),step))|({len(records)-1} if records else set())):
        raw=records[i];t=number(raw.get('t'));valid=clean.get(t,{})
        projected.append({'t':t,'distance':number(raw.get('distance')),
                          'speed':valid.get('speed'),'hr':valid.get('hr'),'cadence':valid.get('cadence'),
                          'elevation':number(raw.get('elevation'))})
    return {'records':projected,'laps':[], 'displaySampled':step>1,'originalSamples':len(records)}


def distance_intervals(records):
    """Segment-only gates; aerobic sampling remains deliberately stricter.

    Cumulative travelled distance is authoritative; no position/heading is read.
    Soft intervals can be tolerated only by a candidate's small total budget.
    """
    out=[]
    for a,b in zip(records,records[1:]):
        dt=b['t']-a['t'];dd=b['distance']-a['distance']
        speed=dd/dt if dt>0 else None;recorded=number(b.get('speed'))
        disagreement=abs(speed-recorded) if speed is not None and recorded is not None else 0
        hard=None;soft=None
        if dt<=0:hard='non-increasing recording time'
        elif dd<0:hard='cumulative distance reset'
        elif dt>10:hard=f'{dt:g} s recording gap'
        elif speed>10:hard='severe GPS inconsistency (distance teleport)'
        elif speed<.5:soft='near-stop'
        elif recorded is not None and disagreement>max(1.5,recorded*.5):
            if disagreement*dt>20:hard='sensor speed disagrees with plausible cumulative distance'
            else:soft='GPS speed/distance wobble'
        if hard is None and speed is not None and speed<.5:soft='near-stop'
        out.append({'dt':dt,'distance':max(0,dd),'speed':speed,'disagreement':disagreement,
                    'hard':hard,'soft':soft,'nearStop':speed is not None and 0<=speed<.5})
    return out


def distance_diagnostics(intervals):
    bad=[r for r in intervals if r['hard'] or r['soft']]
    longest=streak=0
    for r in intervals:
        streak=streak+max(0,r['dt']) if r['hard'] or r['soft'] else 0
        longest=max(longest,streak)
    return {'invalidIntervals':len(bad),'invalidDuration':sum(max(0,r['dt']) for r in bad),
            'longestInvalidInterval':max((r['dt'] for r in bad),default=0),
            'longestQuestionableSection':longest,
            'minimumImpliedSpeed':min((r['speed'] for r in intervals if r['speed'] is not None),default=None),
            'largestSpeedDistanceDisagreement':max((r['disagreement'] for r in intervals),default=0),
            'samplingGapMaximum':max((r['dt'] for r in intervals),default=0),
            'distanceDecreased':any(r['hard']=='cumulative distance reset' for r in intervals),
            'nearStopOrTurnaroundLike':any(r['nearStop'] for r in bad),
            'severe':any(r['hard'] in ('cumulative distance reset','non-increasing recording time') or (r['hard'] or '').startswith('severe GPS') for r in intervals),
            'directionChangeInferred':False}


def series_retry_reason(series, summary):
    """Missing HR/cadence and ordinary stops alone do not warrant FIT downloads."""
    records=(series or {}).get('records',[])
    valid=[r for r in records if number(r.get('t')) is not None and number(r.get('distance')) is not None]
    if len(valid)<3:return 'sensor stream unavailable or parsing produced no usable distance records'
    span=max(r['t'] for r in valid)-min(r['t'] for r in valid)
    if span<=0:return 'sensor timestamps unusable'
    expected=number(summary.get('distance'))
    distance=max(r['distance'] for r in valid)-min(r['distance'] for r in valid)
    if expected and distance<expected*.95:return 'incomplete sensor recording (less than 95% of summary distance)'
    if summary.get('fastestSplit_5000') and expected and expected>=5000 and distance<5000:return 'incomplete sensor recording for reported 5K (less than 5,000 m available)'
    gaps=sum(max(0,b['t']-a['t']) for a,b in zip(valid,valid[1:]) if b['t']-a['t']>10)
    if gaps>max(30,span*.1):return 'substantial missing sensor sections'
    if distance_diagnostics(distance_intervals(valid))['severe']:return 'questionable cumulative distance; retry original FIT parsing'
    return None
