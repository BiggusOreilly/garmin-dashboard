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
