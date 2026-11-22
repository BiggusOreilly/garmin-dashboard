import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from companion import export_run
from companion.garmin import SafeError
from test_fit import synthetic_fit


def document(aid='123', distance=10000, hr=150):
    return {
        'activity': {'garmin_activity_id': aid, 'date': '2026-11-22', 'distance_m': distance},
        'records': [{'heart_rate': hr}],
    }


class ExportFileTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def save(self, data):
        return export_run.save_export(data, self.directory)[0]

    def test_same_id_replaced_and_other_id_untouched(self):
        other = self.save(document('456'))
        other_bytes = other.read_bytes()
        run = self.save(document())
        self.assertEqual(run.name, 'Garmin_Run_2026-11-22_10km_123.json')
        self.assertEqual(self.save(document(hr=160)), run)
        self.assertEqual(json.loads(run.read_text()), document(hr=160))
        self.assertEqual(other.read_bytes(), other_bytes)
        self.assertEqual(set(self.directory.glob('*.json')), {run, other})

    def test_moves_older_filenames_using_content_and_keeps_other_ids(self):
        legacy = self.directory / 'running activity 123 old name.json'
        legacy.write_text(json.dumps({'metadata': {'activityId': 123}}))
        duplicate = self.directory / 'previous.json'
        duplicate.write_text(json.dumps({'activity': {'id': 123}}))
        other = self.directory / 'name contains 123.json'
        other.write_text(json.dumps({'metadata': {'activityId': 456}}))
        path = self.save(document(distance=10040))
        self.assertEqual(path.name, 'Garmin_Run_2026-11-22_10.04km_123.json')
        self.assertEqual(set(self.directory.glob('*.json')), {path, other})
        self.assertEqual(json.loads(other.read_text())['metadata']['activityId'], 456)
        updated = self.save(document(distance=10050))
        self.assertFalse(path.exists())
        self.assertTrue(updated.exists())

    def test_collision_preserves_other_activity(self):
        path = self.directory / 'Garmin_Run_2026-11-22_10km_123.json'
        path.write_text(json.dumps(document('456')))
        original = path.read_bytes()
        with self.assertRaisesRegex(SafeError, 'occupied'):
            self.save(document())
        self.assertEqual(path.read_bytes(), original)

    def test_invalid_json_preserves_prior_export(self):
        path = self.save(document())
        original = path.read_bytes()
        with self.assertRaises(ValueError):
            self.save(document(hr=float('nan')))
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(list(self.directory.glob('*.tmp')), [])

    def test_validation_failure_preserves_prior_export(self):
        path = self.save(document())
        original = path.read_bytes()
        read_export_id = export_run.read_export_id

        def wrong_id_for_temp(candidate):
            return '456' if candidate.suffix == '.tmp' else read_export_id(candidate)

        with patch.object(export_run, 'read_export_id', side_effect=wrong_id_for_temp):
            with self.assertRaisesRegex(SafeError, 'validation'):
                self.save(document(hr=175))
        self.assertEqual(path.read_bytes(), original)

    def test_interruption_at_atomic_replace_rolls_back_name_and_can_retry(self):
        path = self.save(document())
        original = path.read_bytes()
        replace = export_run.os.replace

        def interrupted_replace(source, target):
            if source.suffix == '.tmp':
                raise KeyboardInterrupt
            return replace(source, target)

        with patch.object(export_run.os, 'replace', side_effect=interrupted_replace):
            with self.assertRaises(KeyboardInterrupt):
                self.save(document(distance=12000))
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(list(self.directory.glob('*.json')), [path])
        self.assertEqual(list(self.directory.glob('*.tmp')), [])
        new = self.save(document(distance=12000))
        self.assertEqual(list(self.directory.glob('*.json')), [new])


class ExportDataTests(unittest.TestCase):
    def setUp(self):
        self.run = {
            'activityId': 123, 'activityType': {'typeKey': 'treadmill_running'},
            'startTimeGMT': '2021-09-08 01:46:40', 'startTimeLocal': '2021-09-08 09:46:40',
            'elapsedDuration': 10, 'duration': 9, 'distance': 30,
        }
        self.api = Mock()
        self.api.call.side_effect = self.call

    def call(self, method, *args, **kwargs):
        if method == 'search_activities':
            if kwargs['start'] == 0:
                return [{'activityId': 24, 'activityType': {'typeKey': 'cycling'}},
                        {**self.run, 'activityId': 567, 'isCompleted': False}]
            return [self.run]
        if method == 'get_activity':
            return {'activityId': 123, 'ownerDisplayName': 'Private name',
                    'summaryDTO': {'movingDuration': 8, 'trainingEffect': 3.2, 'token': 'secret'}}
        if method == 'download_activity':
            return synthetic_fit(start=1_000_000_000)
        if method == 'get' and args[0].endswith('/splits'):
            return {'activityId': 123, 'lapDTOs': [{'distance': 30, 'averageHR': 142}]}
        if method == 'get' and args[0].endswith('/weather'):
            return {'temperature': 20, 'weatherTypeDTO': {'desc': 'CLEAR', 'location': 'home'}}
        raise SafeError('Optional endpoint unavailable', 404)

    def test_fresh_lookup_and_full_fit_without_private_fields(self):
        data = export_run.build_export(self.api)
        self.assertEqual(data['activity']['type'], 'treadmill_running')
        self.assertEqual(data['activity']['elapsed_time_s'], 10)
        self.assertEqual(data['activity']['moving_time_s'], 8)
        self.assertEqual(len(data['records']), 3)
        sample = data['records'][1]
        self.assertEqual(sample['cadence'], 87)
        self.assertEqual(sample['calculated']['cadence_steps_per_min'], 174)
        self.assertEqual(sample['calculated']['elapsed_time_s'], 5)
        self.assertAlmostEqual(sample['calculated']['pace_s_per_km'], 1000 / 3)
        self.assertEqual(data['laps']['garmin_connect_laps']['lapDTOs'][0]['averageHR'], 142)
        self.assertEqual(data['environment']['garmin_connect_weather']['temperature'], 20)
        self.assertEqual(len(data['data_quality']['warnings']), 2)
        serialized = json.dumps(data)
        for private in ('Private name', 'secret', 'ownerDisplayName', 'home'):
            self.assertNotIn(private, serialized)

    def test_corrupt_and_empty_fit_rejected(self):
        blob = synthetic_fit(start=1_000_000_000)
        for bad in (b'', blob[:-4], blob[:-1] + bytes([blob[-1] ^ 1])):
            with self.subTest(blob_size=len(bad)), self.assertRaises(SafeError):
                export_run.read_original(bad, None)

    def test_no_runs_and_unexpected_detail_id(self):
        api = Mock()
        api.call.return_value = []
        with self.assertRaisesRegex(SafeError, 'No completed running activities'):
            export_run.latest_run(api)
        self.api.call.side_effect = lambda method, *a, **kw: (
            {'activityId': 456} if method == 'get_activity' else self.call(method, *a, **kw)
        )
        with self.assertRaisesRegex(SafeError, 'expected activity ID'):
            export_run.build_export(self.api)
