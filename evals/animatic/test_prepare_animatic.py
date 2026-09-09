import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('prepare_animatic', ROOT / 'scripts' / 'prepare_animatic.py')
media = importlib.util.module_from_spec(spec)
spec.loader.exec_module(media)
spec = importlib.util.spec_from_file_location('media_builder', Path(__file__).with_name('build_media_fixtures.py'))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class SamplingTests(unittest.TestCase):
    def test_dependency_error_has_configuration(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(media.shutil, 'which', return_value=None), patch.object(media.Path, 'is_file', return_value=False):
            with self.assertRaisesRegex(media.MediaError, 'REVIEWER_FFMPEG'):
                media.executable('ffmpeg')

    def test_short_shot_and_cut_neighbors_not_lost(self):
        frames = [{'time_seconds': t} for t in [0, .1, .4, .9, 1.4]]
        indices = media.sample_indices(frames, [0, 2, 3, 5], samples=2)
        self.assertEqual(indices, [0, 1, 2, 3, 4])

    def test_anchor_and_dense_use_timestamps(self):
        frames = [{'time_seconds': t} for t in [0, .1, .4, .9, 1.4]]
        self.assertEqual(media.sample_indices(frames, [0, 5], samples=2, anchor_times=[.41],
            dense_ranges=[{'start_seconds': .8, 'end_seconds': 1}]), [0, 2, 3, 4])


class RealMediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.ffmpeg, cls.ffprobe = media.executable('ffmpeg'), media.executable('ffprobe')
        except media.MediaError as exc:
            raise unittest.SkipTest(str(exc))
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        builder.build(cls.root / 'source', cls.ffmpeg)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def prepare(self, name, **kwargs):
        return media.prepare(self.root / 'source' / name, self.root / self._testMethodName,
                             ffmpeg=self.ffmpeg, ffprobe=self.ffprobe, **kwargs)

    def test_hardcut_one_frame_shot_and_unreviewed_manifest(self):
        report = self.prepare('hard-cut.mkv')
        self.assertEqual([x['time_seconds'] for x in report['cut_candidates']], [.5, .6])
        self.assertTrue(report['coverage']['decode_completed'])
        self.assertFalse(report['coverage']['visual_inspection_completed'])
        self.assertEqual(report['coverage']['reviewed_shot_ids'], [])
        self.assertIn(5, [x['frame_index'] for x in report['extracted_frames']])
        self.assertTrue(all(Path(x['ref']).is_file() for x in report['extracted_frames']))
        self.assertEqual(report['audio']['status'], 'not_applicable')

    def test_vfr_uses_real_pts(self):
        report = self.prepare('vfr.mkv')
        self.assertEqual([x['time_seconds'] for x in report['frames']], [0, .1, .4, .9, 1.4])

    def test_digital_silence(self):
        report = self.prepare('silent.mkv')
        self.assertEqual(report['audio'], {'status':'not_applicable','method':'skipped_by_scope','checked_ranges':[],'evidence':[]})
        self.assertEqual(list((self.root/self._testMethodName).glob('*.wav')),[])

    def test_non_silent_not_misclassified(self):
        with patch.object(media,'run',wraps=media.run) as calls:
            report = self.prepare('tone.mkv')
        self.assertEqual(report['audio']['status'], 'not_applicable')
        commands=[list(map(str,c.args[0])) for c in calls.call_args_list]
        self.assertTrue(all('-af' not in c and '-vn' not in c and not any(x.endswith('.wav') for x in c) for c in commands))
        self.assertEqual(list((self.root/self._testMethodName).glob('*.wav')),[])

    def test_fade_not_auto_confirmed_as_hardcut(self):
        report = self.prepare('fade.mkv')
        self.assertTrue(all(not cut['verified'] for cut in report['cut_candidates']))
        self.assertTrue(any('slow transitions' in s for s in report['coverage']['limitations']))

    def test_provided_segment_unverified(self):
        report = self.prepare('hard-cut.mkv', provided_segments=[{'shot_id': 'WRONG', 'start_seconds': 0, 'end_seconds': .4}])
        self.assertFalse(report['provided_segments_verified'])
        self.assertTrue(all(s['shot_id'] is None for s in report['candidate_segments']))

    def test_corrupt_video_fails(self):
        with self.assertRaises(media.MediaError):
            self.prepare('damaged.mkv')

    def test_invalid_range_fails_before_output(self):
        with self.assertRaisesRegex(media.MediaError, 'outside'):
            self.prepare('hard-cut.mkv', anchor_times=[100])

    def test_existing_directory_preserved(self):
        (self.root / self._testMethodName).mkdir()
        with self.assertRaisesRegex(media.MediaError, 'already exists'):
            self.prepare('hard-cut.mkv')


if __name__ == '__main__':
    unittest.main()
