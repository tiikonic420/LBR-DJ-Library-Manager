"""Real, generated fixtures only; FFmpeg is a test dependency, not an app requirement."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'Sources_application'), str(Path(__file__).resolve().parents[1] / 'Sources_application/modules')]
import tag_engine
from library_services import audio_info, batch_plan, apply_batch
from reliability import BackupStore, digest


@unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg unavailable: generate fixtures on validation host')
class AudioFormats(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = BackupStore(self.root / 'backups')

    def check_format(self, suffix, codec):
        path = self.root / ('fictif' + suffix)
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.3', '-c:a', codec, str(path)], check=True, timeout=20, capture_output=True)
        info = audio_info(path)
        self.assertFalse(info['error'])
        self.assertGreater(info['duration'], 0)
        pcm = lambda: subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 's16le', '-'], capture_output=True, check=True, timeout=20).stdout
        audio_before = pcm()
        tag_engine.write_tags(str(path), {'title': 'OLD', 'artist': 'LBR', 'comment': 'CONSERVER'})
        tagged_bytes = path.read_bytes()
        plan = batch_plan([path], [{'field': 'title', 'action': 'set', 'value': 'Été Réunion'}], [self.root])
        identifier = apply_batch(plan, [self.root], self.store)
        tags = tag_engine.read_tags(str(path))
        self.assertEqual(tags['title'], 'Été Réunion')
        self.assertEqual(tags['artist'], 'LBR')
        self.assertEqual(tags['comment'], 'CONSERVER')
        self.assertEqual(pcm(), audio_before)
        self.store.restore(identifier)
        self.assertEqual(path.read_bytes(), tagged_bytes)

    def test_mp3(self):
        self.check_format('.mp3', 'libmp3lame')

    def test_flac(self):
        self.check_format('.flac', 'flac')

    def test_m4a_aac(self):
        self.check_format('.m4a', 'aac')

    def test_alac(self):
        self.check_format('.m4a', 'alac')

    def test_wav(self):
        self.check_format('.wav', 'pcm_s16le')

    def test_aiff(self):
        self.check_format('.aiff', 'pcm_s16be')

    def test_raw_aac_read_and_failed_write_preserves_original(self):
        path = self.root / 'fictif.aac'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.3', '-c:a', 'aac', str(path)], check=True, timeout=20, capture_output=True)
        self.assertFalse(audio_info(path)['error'])
        original = path.read_bytes()
        plan = batch_plan([path], [{'field': 'title', 'action': 'set', 'value': 'NEW'}], [self.root])
        with self.assertRaises(Exception):
            apply_batch(plan, [self.root], self.store)
        self.assertEqual(path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main(verbosity=2)
