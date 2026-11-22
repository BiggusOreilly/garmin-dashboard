"""Export the newest Garmin run without starting or updating the dashboard."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile

from .fit import fit_messages
from .garmin import Garmin, SafeError
from .quality import number


# Explicit projection keeps account data, free text and location out of the export.
CONNECT_UNITS = {
    'distance': 'm', 'duration': 's (Garmin activity duration)',
    'elapsedDuration': 's', 'movingDuration': 's',
    'averageHR': 'bpm', 'maxHR': 'bpm', 'minHR': 'bpm',
    'averageSpeed': 'm/s', 'maxSpeed': 'm/s',
    'averageMovingSpeed': 'm/s', 'averageRunCadence': 'steps/min',
    'maxRunCadence': 'steps/min',
    'averageRunningCadenceInStepsPerMinute': 'steps/min',
    'maxRunningCadenceInStepsPerMinute': 'steps/min', 'steps': 'steps',
    'avgStrideLength': 'cm', 'averageStrideLength': 'cm',
    'avgGroundContactTime': 'ms', 'avgVerticalOscillation': 'cm',
    'avgVerticalRatio': '%', 'avgGroundContactBalance': '%',
    'elevationGain': 'm', 'elevationLoss': 'm', 'minElevation': 'm', 'maxElevation': 'm',
    'calories': 'kcal', 'bmrCalories': 'kcal', 'averagePower': 'W', 'maxPower': 'W',
    'normalizedPower': 'W', 'avgPower': 'W', 'vo2MaxValue': 'mL/(kg·min)',
    'vO2MaxValue': 'mL/(kg·min)', 'trainingEffect': 'Garmin score',
    'aerobicTrainingEffect': 'Garmin score', 'anaerobicTrainingEffect': 'Garmin score',
    'activityTrainingLoad': 'Garmin load score', 'trainingLoad': 'Garmin load score',
    'recoveryTime': 'min', 'minTemperature': '°C', 'maxTemperature': '°C',
    'avgTemperature': '°C', 'averageTemperature': '°C', 'lapIndex': 'index',
    'totalExerciseTime': 's', 'totalDistance': 'm', 'totalDuration': 's',
    'noOfSplits': 'count', 'bestSplitIndex': 'index',
    'temperature': '°C', 'apparentTemperature': '°C', 'relativeHumidity': '%',
    'windSpeed': 'Garmin source unit unspecified', 'windDirection': 'degrees',
    'windGust': 'Garmin source unit unspecified',
    'dewPoint': '°C',
    **{f'hrTimeInZone_{i}': 's' for i in range(1, 6)},
    **{f'powerTimeInZone_{i}': 's' for i in range(1, 8)},
}
CONNECT_CONTAINERS = {
    'lapDTOs', 'laps', 'splitDTOs', 'splits', 'splitSummaries', 'splitSummaryDTOs',
    'activityWeatherDTO', 'weather', 'weatherTypeDTO', 'activityLaps',
}
FIT_MESSAGES = {
    'record', 'lap', 'session', 'split', 'split_summary', 'weather_conditions',
    'time_in_zone', 'hr', 'hrv', 'event',
}
FIT_ENUMS = {
    'sport', 'sub_sport', 'event', 'event_type', 'lap_trigger', 'intensity',
    'split_type', 'condition', 'weather_report', 'day_of_week',
}
FIT_DEVELOPER_METRICS = {
    'power', 'form_power', 'air_power', 'cadence', 'ground_contact_time',
    'vertical_oscillation', 'vertical_ratio', 'stride_length', 'step_length',
    'leg_spring_stiffness', 'running_effectiveness', 'temperature',
}
FIT_PRIVATE = (
    'position', 'latitude', 'longitude', '_lat', '_long', 'semicircles',
    'serial', 'device', 'manufacturer', 'product', 'user', 'location', 'name',
    'course', 'workout', 'ant_', 'message_index', 'gps', 'zone_id',
)


def activity_id(value):
    if type(value) not in (int, str):
        return None
    text = str(value)
    if re.fullmatch(r'[0-9]{1,24}', text) and int(text) > 0:
        return str(int(text))
    return None


def timestamp(value):
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
        except ValueError:
            pass
    return None


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def latest_run(api):
    offset = 0
    seen = set()
    while True:
        # Garmin's activity history is newest first. Scan mixed pages to include
        # running subtypes even if an API activity-type filter omits one.
        page = api.call('search_activities', start=offset, limit=99)
        if not isinstance(page, list):
            raise SafeError('Garmin returned an unexpected activity list.')
        if not page:
            raise SafeError('No completed running activities were found in Garmin Connect.')
        candidates = []
        page_ids = set()
        for item in page:
            aid = activity_id(item.get('activityId')) if isinstance(item, dict) else None
            if aid is None:
                raise SafeError('Garmin returned an activity without a valid ID.')
            page_ids.add(aid)
            kind = item.get('activityType') or item.get('activityTypeDTO') or {}
            key = kind.get('typeKey', '') if isinstance(kind, dict) else ''
            type_key = key.lower() if isinstance(key, str) else ''
            is_run = 'running' in type_key or type_key == 'run' or type_key.endswith('_run')
            if not is_run or item.get('isCompleted') is False or item.get('isInProgress') is True:
                continue
            start = timestamp(item.get('startTimeGMT') or item.get('startTimeLocal'))
            if start is None:
                raise SafeError('A Garmin run has no usable start time. Try again after Garmin finishes syncing.')
            if item.get('startTimeGMT') and utc(start) > datetime.now(timezone.utc):
                continue
            candidates.append((utc(start), int(aid), item, key))
        if not page_ids - seen:
            raise SafeError('Garmin repeated an activity page. Try exporting again later.')
        if candidates:
            _, aid, item, key = max(candidates, key=lambda row: row[:2])
            return str(aid), item, key
        seen.update(page_ids)
        offset += len(page)


def connect_fields(payload, *, weather=False):
    if isinstance(payload, list):
        return [connect_fields(row, weather=weather) for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return {}
    fields = {}
    for key, value in payload.items():
        if key in CONNECT_UNITS and number(value) is not None:
            fields[key] = value
        elif key in CONNECT_CONTAINERS and isinstance(value, (dict, list)):
            fields[key] = connect_fields(value, weather=key == 'weatherTypeDTO')
        elif key in ('startTimeGMT', 'startTimeLocal', 'endTimeGMT', 'endTimeLocal'):
            if timestamp(value) is not None:
                fields[key] = value
        elif key in ('splitType', 'weatherType', 'trainingEffectLabel',
                     'aerobicTrainingEffectMessage', 'anaerobicTrainingEffectMessage'):
            # Preserve Garmin's enumerated codes without carrying arbitrary text.
            if isinstance(value, str) and re.fullmatch(r'[A-Z][A-Z0-9_]{0,79}', value):
                fields[key] = value
        elif weather and key in ('desc', 'description') and isinstance(value, str):
            if re.fullmatch(r'[A-Za-z][A-Za-z /-]{0,59}', value):
                fields[key] = value
    return fields


def fit_value(value, enum=False):
    if isinstance(value, datetime):
        return utc(value).isoformat()
    if number(value) is not None or (enum and isinstance(value, str)):
        return value
    if isinstance(value, (tuple, list)):
        return [fit_value(item, enum) for item in value]
    return None


def pace(speed):
    speed = number(speed)
    return 1000 / speed if speed is not None and speed > 0 else None


def read_original(blob, start_utc):
    messages = {name: [] for name in sorted(FIT_MESSAGES)}
    definitions = {}
    try:
        for frame in fit_messages(blob, strict=True):
            if frame.name not in messages:
                continue
            row = {}
            for field in frame.fields:
                name = field.name
                is_developer = getattr(field.field_def, 'is_dev', False)
                if (field.field is None or name in ('data', 'data16')
                        or any(part in name.lower() for part in FIT_PRIVATE)
                        or (is_developer and name.lower().replace(' ', '_') not in FIT_DEVELOPER_METRICS)):
                    continue
                if is_developer:
                    # Keep recognized sensor extensions separate from standard FIT fields.
                    name = f'developer_{field.field_def.dev_data_index}_{name}'
                value = fit_value(field.value, name in FIT_ENUMS)
                if value is None or isinstance(value, list) and all(v is None for v in value):
                    continue
                row[name] = value
                unit = field.units or {
                    'relative_humidity': '%', 'precipitation_probability': '%',
                }.get(name)
                if isinstance(field.value, datetime):
                    unit = 'UTC timestamp (ISO 8601)'
                if name == 'local_timestamp':
                    # Local FIT time is encoded as a wall-clock offset from the epoch.
                    row[name] = field.value.isoformat().split('+')[0] if isinstance(field.value, datetime) else value
                    unit = 'local wall-clock timestamp'
                if 'cadence' in name and unit == 'rpm':
                    unit = 'strides/min (FIT running cadence)'
                definitions.setdefault(frame.name, {})[name] = {
                    'unit': unit or 'unitless FIT code or count',
                    'definition': name.replace('_', ' '),
                }
            messages[frame.name].append(row)
    except Exception:
        raise SafeError('Garmin’s original FIT download is damaged or could not be decoded. Try again after it finishes syncing.') from None
    records = messages['record']
    if not records or any(not timestamp(row.get('timestamp')) for row in records):
        raise SafeError('Garmin’s original FIT file is missing timestamped activity samples. Try again after it finishes syncing.')
    session = next((row for row in messages['session'] if row.get('sport') == 'running'), {})
    start = timestamp(session.get('start_time')) or start_utc
    previous = None
    for row in records:
        current = utc(timestamp(row['timestamp']))
        if previous is not None and current < previous:
            raise SafeError('Garmin’s original FIT file contains out-of-order sample timestamps.')
        previous = current
        cadence = row.get('cadence')
        row['calculated'] = {
            'elapsed_time_s': (current - utc(start)).total_seconds() if start is not None else None,
            'pace_s_per_km': pace(row.get('enhanced_speed', row.get('speed'))),
            'cadence_steps_per_min': 2 * (cadence + row.get('fractional_cadence', 0)) if cadence is not None else None,
        }
    for kind in ('lap', 'split'):
        for row in messages[kind]:
            row['calculated'] = {
                'average_pace_s_per_km': pace(row.get('enhanced_avg_speed', row.get('avg_speed'))),
                'average_cadence_steps_per_min': (
                    2 * (row['avg_running_cadence'] + row.get('avg_fractional_cadence', 0))
                    if 'avg_running_cadence' in row else None
                ),
            }
    return messages, definitions, session


def optional_detail(api, aid, endpoint, warnings):
    try:
        return api.call('get', f'/activity-service/activity/{aid}/{endpoint}')
    except SafeError as err:
        if err.status not in (400, 403, 404, 405, 501):
            raise
        warnings.append(f'Garmin Connect did not provide the optional {endpoint} dataset.')
        return None


def build_export(api):
    aid, item, kind = latest_run(api)
    detail = api.call('get_activity', aid)
    if not isinstance(detail, dict) or activity_id(detail.get('activityId')) != aid:
        raise SafeError('Garmin detail did not contain the expected activity ID.')
    summary = {**item, **(detail.get('summaryDTO') or {})} if isinstance(detail.get('summaryDTO'), dict) else item
    start = timestamp(summary.get('startTimeGMT'))
    local = timestamp(summary.get('startTimeLocal'))
    messages, definitions, session = read_original(api.call('download_activity', aid), start)
    start = start or timestamp(session.get('start_time'))
    distance = number(summary.get('distance'))
    if distance is None:
        distance = number(session.get('total_distance'))
    elapsed = number(summary.get('elapsedDuration'))
    if elapsed is None:
        elapsed = number(session.get('total_elapsed_time'))
    duration = number(summary.get('duration')) or number(session.get('total_timer_time'))
    if (distance is None or distance < 0 or max(elapsed or 0, duration or 0) <= 0
            or (local is None and start is None)):
        raise SafeError('Garmin has not provided a complete run summary. Try again after it finishes syncing.')
    warnings = []
    records = messages['record']
    recorded_distances = [row['distance'] for row in records if number(row.get('distance')) is not None]
    original_distance = number(session.get('total_distance'))
    expected_distance = original_distance if original_distance and original_distance > 0 else distance
    if len(records) < 2 or (expected_distance > 100 and recorded_distances
                           and max(recorded_distances) < .95 * expected_distance):
        raise SafeError('Garmin’s original FIT recording appears incomplete. Try again after it finishes syncing.')
    if not recorded_distances:
        warnings.append('The original FIT contains no cumulative sample distances.')
    optional = {}
    for endpoint in ('splits', 'typedsplits', 'split_summaries', 'weather'):
        data = optional_detail(api, aid, endpoint, warnings)
        if isinstance(data, dict) and 'activityId' in data and activity_id(data['activityId']) != aid:
            raise SafeError(f'Garmin’s {endpoint} dataset did not match the expected activity ID.')
        fields = connect_fields(data)
        if data and not fields:
            warnings.append(f'Garmin’s optional {endpoint} response contained no recognized metrics.')
        optional[endpoint] = fields
    connect = connect_fields({**item, **detail, **summary})
    connect = {key: value for key, value in connect.items() if key not in CONNECT_CONTAINERS}
    avg_speed = connect.get('averageSpeed', session.get('enhanced_avg_speed', session.get('avg_speed')))
    max_speed = connect.get('maxSpeed', session.get('enhanced_max_speed', session.get('max_speed')))
    laps = messages['lap']
    if number(session.get('num_laps')) and len(laps) < session['num_laps']:
        warnings.append('The original FIT contains fewer lap records than its session reports.')
    lap_distance = 0
    km_laps = []
    for index, lap in enumerate(laps, 1):
        length = number(lap.get('total_distance'))
        if length is None:
            break
        lap_distance += length
        km = round(lap_distance / 1000)
        if abs(length - 1000) <= 1 and abs(lap_distance - km * 1000) <= 1:
            km_laps.append({'kilometre': km, 'fit_lap_number': index})
    if not laps and not optional['splits']:
        warnings.append('Garmin supplied no lap records.')
    return {
        'schema_version': 1,
        'activity': {
            'garmin_activity_id': aid, 'date': (local or start).date().isoformat(),
            'start_time_local': local.isoformat() if local else None,
            'start_time_utc': utc(start).isoformat() if start else None,
            'type': kind, 'distance_m': distance, 'elapsed_time_s': elapsed,
            'moving_time_s': connect.get('movingDuration', session.get('total_moving_time')),
            'fit_timer_time_s': session.get('total_timer_time'),
        },
        'summary': {
            'average_heart_rate_bpm': connect.get('averageHR', session.get('avg_heart_rate')),
            'max_heart_rate_bpm': connect.get('maxHR', session.get('max_heart_rate')),
            'average_cadence_steps_per_min': next((connect[k] for k in
                ('averageRunningCadenceInStepsPerMinute', 'averageRunCadence') if k in connect),
                2 * (session['avg_running_cadence'] + session.get('avg_fractional_cadence', 0))
                if 'avg_running_cadence' in session else None),
            'max_cadence_steps_per_min': next((connect[k] for k in
                ('maxRunningCadenceInStepsPerMinute', 'maxRunCadence') if k in connect),
                2 * (session['max_running_cadence'] + session.get('max_fractional_cadence', 0))
                if 'max_running_cadence' in session else None),
            'calculated': {'average_pace_s_per_km': pace(avg_speed),
                           'best_pace_s_per_km': pace(max_speed)},
            'garmin_connect_recorded': connect,
            'fit_sessions': messages['session'],
        },
        'records': records,
        'laps': {'fit_laps': laps, 'garmin_connect_laps': optional['splits'],
                 'garmin_connect_embedded': {k: v for k, v in connect_fields(detail).items()
                                             if k in CONNECT_CONTAINERS and 'weather' not in k.lower()}},
        'splits': {'fit_splits': messages['split'], 'fit_split_summaries': messages['split_summary'],
                   'garmin_connect_typed_splits': optional['typedsplits'],
                   'garmin_connect_split_summaries': optional['split_summaries'],
                   'recorded_kilometre_lap_references': km_laps},
        'environment': {'fit_weather': messages['weather_conditions'],
                        'garmin_connect_weather': optional['weather'] or connect_fields(detail).get('weather')
                        or connect_fields(detail).get('activityWeatherDTO')},
        'additional_fit_messages': {name: messages[name] for name in ('time_in_zone', 'hr', 'hrv', 'event')},
        'field_definitions': {
            'fit': definitions, 'garmin_connect_units': CONNECT_UNITS,
            'calculated': {
                'elapsed_time_s': 'Seconds since FIT running session start, or Garmin UTC activity start. Includes pauses.',
                'pace_s_per_km': 'Seconds per kilometre from recorded speed (1000 / speed in m/s). Null at zero speed.',
                'average_pace_s_per_km': 'Seconds per kilometre from the source average speed.',
                'best_pace_s_per_km': 'Seconds per kilometre at the source maximum speed.',
                'cadence_steps_per_min': 'Total steps per minute, twice FIT running cadence including its recorded fractional component when present.',
                'average_cadence_steps_per_min': 'Total steps per minute, twice the FIT average running cadence including its recorded fractional component when present.',
            },
            'activity': {
                'garmin_activity_id': 'Garmin Connect activity identifier, stored as a string.',
                'type': 'Garmin Connect activity type key.',
                'start_time_local': 'Garmin local start time in ISO 8601.',
                'start_time_utc': 'Activity start time in UTC, ISO 8601.',
                'distance_m': 'Total distance in metres, from Garmin Connect or FIT session.',
                'elapsed_time_s': 'Wall-clock duration in seconds, including pauses.',
                'moving_time_s': 'Garmin-reported time moving in seconds, if recorded.',
                'fit_timer_time_s': 'FIT timer duration in seconds, excluding timer stops.',
                'date': 'Local calendar date when provided by Garmin, otherwise UTC.',
            },
            'summary': {
                'average_heart_rate_bpm': 'Source average heart rate in beats per minute.',
                'max_heart_rate_bpm': 'Source maximum heart rate in beats per minute.',
                'average_cadence_steps_per_min': 'Average total steps per minute, from Garmin Connect or converted from FIT strides per minute.',
                'max_cadence_steps_per_min': 'Maximum total steps per minute, from Garmin Connect or converted from FIT strides per minute.',
            },
            'fit_step_length': 'Distance from one footfall to the next, in the units given by the FIT profile.',
            'fit_stance_time': 'Ground contact time per footfall, in milliseconds.',
            'recorded_kilometre_lap_references': 'One-based references to FIT laps within one metre of a kilometre and aligned to a cumulative kilometre boundary.',
        },
        'data_quality': {'fit_record_count': len(records), 'warnings': warnings},
    }


def export_id(document):
    if not isinstance(document, dict):
        return None
    containers = [document] + [document.get(key) for key in ('activity', 'metadata', 'activity_metadata')]
    ids = {
        activity_id(row[key])
        for row in containers if isinstance(row, dict)
        for key in ('garmin_activity_id', 'garminActivityId', 'activity_id', 'activityId')
        if key in row
    }
    if not ids:
        # Older exports may use a plain id inside an activity object.
        activity = document.get('activity')
        if isinstance(activity, dict):
            return activity_id(activity.get('id'))
    return ids.pop() if len(ids) == 1 else None


def read_export_id(path):
    if path.is_symlink() or not path.is_file():
        return None
    try:
        with path.open(encoding='utf-8') as handle:
            return export_id(json.load(handle))
    except (ValueError, UnicodeError):
        return None


def save_export(document, directory):
    aid = document['activity']['garmin_activity_id']
    if activity_id(aid) != aid or not document.get('records'):
        raise SafeError('The export did not contain the expected activity ID and samples.')
    day = datetime.fromisoformat(document['activity']['date']).date().isoformat()
    distance = f"{document['activity']['distance_m'] / 1000:.3f}".rstrip('0').rstrip('.')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = directory / f'Garmin_Run_{day}_{distance}km_{aid}.json'
    # Serialize scan/migration/replace for simultaneous launcher invocations.
    with (directory / '.export.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        existing = []
        for path in sorted(directory.glob('*.json')):
            owner = read_export_id(path)
            if owner == aid:
                existing.append(path)
            elif path == destination:
                raise SafeError('The export filename is occupied by a file with a different or unreadable activity ID.')
        temporary = None
        migrated = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=directory,
                                             prefix='.garmin-run-', suffix='.tmp', delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(document, handle, ensure_ascii=False, allow_nan=False, indent=2)
                handle.write('\n')
                handle.flush()
                os.fsync(handle.fileno())
            if read_export_id(temporary) != aid:
                raise SafeError('The saved export did not pass activity ID validation.')
            if existing and destination not in existing:
                # Move the old file first so a filename change never creates another
                # copy. An interruption here leaves the previous content intact.
                migrated = existing[0]
                os.replace(migrated, destination)
            try:
                os.replace(temporary, destination)
            except BaseException:
                if migrated is not None and temporary.exists():
                    os.replace(destination, migrated)
                raise
            warnings = []
            for old in existing:
                if old != migrated and old != destination:
                    try:
                        old.unlink()
                    except OSError:
                        warnings.append(f'Could not remove the verified older export {old.name}. Check its permissions and run the launcher again.')
            return destination, warnings
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def interrupted(signum, frame):
    raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reveal', action='store_true', help='Select the export in macOS Finder')
    args = parser.parse_args()
    signal.signal(signal.SIGHUP, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    try:
        print('Checking Garmin Connect for your latest completed run…', flush=True)
        api = Garmin()
        try:
            document = build_export(api)
        finally:
            api.close()
        path, warnings = save_export(document, Path.home() / 'Downloads' / 'Garmin Runs')
        print(f'Exported {document["data_quality"]["fit_record_count"]} samples to {path}')
        for warning in document['data_quality']['warnings'] + warnings:
            print(f'Warning: {warning}', file=sys.stderr)
    except SafeError as err:
        print(f'Export stopped. {err}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\nExport interrupted. Any completed JSON file remains valid.', file=sys.stderr)
        return 130
    except PermissionError:
        print('Export stopped. Check that Terminal can access Downloads and that the Garmin configuration and output folder are writable.', file=sys.stderr)
        return 1
    except OSError:
        print('Export stopped. Check available disk space and access to the Garmin configuration and Downloads folders.', file=sys.stderr)
        return 1
    except (ValueError, TypeError, OverflowError):
        print('Export stopped. Garmin returned data that could not be validated as JSON.', file=sys.stderr)
        return 1
    except ModuleNotFoundError:
        print('Export stopped. Double-click Setup Garmin Dashboard.command to install the project dependencies.', file=sys.stderr)
        return 1
    if args.reveal:
        try:
            subprocess.run(['/usr/bin/open', '-R', str(path)], check=True)
        except (OSError, subprocess.CalledProcessError):
            print('The JSON was saved. Finder could not select it automatically.', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
