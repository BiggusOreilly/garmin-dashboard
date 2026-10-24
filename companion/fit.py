"""Read original official-download FIT locally; deliberately discard coordinates."""
from io import BytesIO
from zipfile import ZipFile, is_zipfile

def parse_fit(blob):
    import fitdecode
    stream=BytesIO(blob)
    if is_zipfile(stream):
        with ZipFile(stream) as z:
            names=[x for x in z.infolist() if x.filename.lower().endswith('.fit') and x.file_size<=100_000_000]
            if not names: return {'records':[],'laps':[]}
            blob=z.read(names[0])
    records=[];laps=[];start=None
    with fitdecode.FitReader(BytesIO(blob)) as reader:
        for frame in reader:
            if not isinstance(frame,fitdecode.FitDataMessage): continue
            if frame.name not in ('record','lap'): continue
            values={f.name:f.value for f in frame.fields}
            if frame.name=='record':
                timestamp=values.get('timestamp')
                if timestamp is None: continue
                if start is None:start=timestamp
                speed=values.get('enhanced_speed',values.get('speed'))
                cadence=values.get('cadence')
                # FIT running cadence is strides/min; show steps/min.
                delta=timestamp-start
                elapsed=delta.total_seconds() if hasattr(delta,'total_seconds') else float(delta)
                row={'t':elapsed,'distance':values.get('distance'),'speed':speed,'hr':values.get('heart_rate'),'cadence':(cadence+(values.get('fractional_cadence') or 0))*2 if cadence is not None else None,'elevation':values.get('enhanced_altitude',values.get('altitude'))}
                records.append(row)
            else:
                laps.append({'distance':values.get('total_distance'),'duration':values.get('total_timer_time'),'hr':values.get('avg_heart_rate'),'cadence':values.get('avg_running_cadence')})
    return {'records':records,'laps':laps}
