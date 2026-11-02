import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import uuid
import wave
root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root / 'Sources_application'), str(root / 'Sources_application/modules')]
from reliability import BackupStore, Conflict
from legacy_safety import install


class Adapters(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.wav = self.path / 'fictif.wav'
        with wave.open(str(self.wav), 'wb') as stream:
            stream.setparams((2, 2, 44100, 0, 'NONE', 'none'))
            stream.writeframes(b'\0' * 4000)
        self.original = self.wav.read_bytes()
        self.store = BackupStore(self.path / 'backups')
        self.workspace = SimpleNamespace(store=self.store, checkpoint=lambda: None, pending_snapshots=[], confirm_plan=lambda plan: False)
        self.workspace.app = SimpleNamespace(hub=SimpleNamespace(ui=lambda fn, *a, **kw: fn(*a, **kw)))

    def module(self, name):
        spec = importlib.util.spec_from_file_location('test_' + uuid.uuid4().hex, root / 'Sources_application/modules' / (name + '.py'))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_musicgenre_backed_up_and_readback(self):
        mod = self.module('musicgenre_v2')
        install('MusicGenre', mod, self.workspace)
        mod.write_tags(str(self.wav), 'MALOYA', '2026')
        self.assertEqual(mod.read_tags(str(self.wav)), ('MALOYA', '2026'))
        identifier = self.store.list()[0]['id']
        self.store.restore(identifier)
        self.assertEqual(self.wav.read_bytes(), self.original)

    def test_musicgenre_failed_backup_no_write(self):
        mod = self.module('musicgenre_v2')
        writer = mod.write_tags = Mock()
        install('MusicGenre', mod, self.workspace)
        with patch.object(self.store, 'create', side_effect=PermissionError('synthetic')):
            with self.assertRaises(PermissionError):
                mod.write_tags(str(self.wav), 'NEW', '2026')
        writer.assert_not_called()

    def test_musicgenre_preview_cancel_blocks_apply(self):
        mod = self.module('musicgenre_v2')
        apply = mod.App.apply = Mock()
        install('MusicGenre', mod, self.workspace)
        controller = SimpleNamespace(rows=[(str(self.wav), 'OLD', 'NEW', '2025', '2026', 'À modifier')])
        mod.App.apply(controller)
        apply.assert_not_called()
        self.assertEqual(self.store.list(), [])

    def test_tagstudio_common_snapshot_and_preview_cancel(self):
        mod = self.module('tag_studio')
        original_save = mod.App.save = Mock()
        install('TagStudio', mod, self.workspace)
        controller = SimpleNamespace(pending={str(self.wav): {'title': 'NEW'}})
        mod.App.save(controller)
        original_save.assert_not_called()
        old_backup = mod.safe_write(str(self.wav), {'title': 'NEW'}, self.path / 'legacy_backups')
        self.assertIn(old_backup, mod._lbr_backup_ids)
        self.store.restore(mod._lbr_backup_ids[old_backup])
        self.assertEqual(self.wav.read_bytes(), self.original)

    def test_cover_preview_cancel_is_non_destructive(self):
        mod = self.module('tag_studio')
        cover = mod.App.apply_cover = Mock()
        install('TagStudio', mod, self.workspace)
        mod.App.apply_cover(SimpleNamespace(), [str(self.wav)], b'PNG', 'image/png', 'replace')
        cover.assert_not_called()
        self.assertEqual(self.wav.read_bytes(), self.original)

    def test_serato_wav_rejection_and_backup_fail_blocks_injection(self):
        mod = self.module('rekordbox_serato_v1_4')
        install('Serato', mod, self.workspace)
        with self.assertRaises(RuntimeError):
            mod.inject_serato_markers(str(self.wav), [], [])
        self.assertEqual(self.store.list(), [])
        fake = self.path / 'fictif.mp3'
        fake.write_bytes(b'SYNTHETIC')
        with patch.object(self.store, 'create', side_effect=PermissionError('locked')):
            with self.assertRaises(PermissionError):
                mod.inject_serato_markers(str(fake), [], [])
        self.assertEqual(fake.read_bytes(), b'SYNTHETIC')

    def test_rekordbox_closed_snapshot_includes_wal_and_does_not_invoke_cli(self):
        mod = self.module('rekordsync_v5_0_6')
        db = self.path / 'master.db'
        db.write_bytes(b'FAKE DATABASE')
        Path(str(db) + '-wal').write_bytes(b'FAKE WAL')
        mod.master_db_path = lambda: db
        mod.rb_running = lambda: False
        mod.run_process = Mock(side_effect=AssertionError('CLI forbidden in synthetic snapshot test'))
        install('RekordSync', mod, self.workspace)
        copies = mod.backup_master_db()
        self.assertEqual(len(copies), 2)
        self.assertEqual(len(self.workspace.pending_snapshots), 1)
        mod.rb_running = lambda: True
        with self.assertRaises(Conflict):
            mod.backup_master_db()
        mod.run_process.assert_not_called()

    def test_rekordsync_preview_failure_blocks_sync(self):
        mod = self.module('rekordsync_v5_0_6')
        sync = mod.App.sync_one_click = Mock()
        install('RekordSync', mod, self.workspace)
        controller = SimpleNamespace(generate=lambda: [(self.path / 'Maloya', self.path / 'synthetic.m3u8', 1)], playlist_arg=lambda name: name, cmd=lambda args: (1, 'Synthetic CLI failure'))
        with self.assertRaises(Conflict):
            mod.App.sync_one_click(controller)
        sync.assert_not_called()

    def test_rename_preserves_bytes_and_backup_restores_source_without_deletion(self):
        mod = self.module('tag_studio')
        mod.simpledialog.askstring = Mock(return_value='{artist} - {title}')
        self.workspace.confirm_plan = lambda plan: True
        install('TagStudio', mod, self.workspace)
        controller = SimpleNamespace(selected=lambda: [str(self.wav)], rows={str(self.wav): {'artist': 'LBR', 'title': 'NEW'}}, pending={}, backups=[], populate=Mock())
        mod.App.rename(controller)
        target = self.path / 'LBR - NEW.wav'
        self.assertFalse(self.wav.exists())
        self.assertEqual(target.read_bytes(), self.original)
        identifier = self.store.list()[0]['id']
        self.store.restore(identifier)
        self.assertEqual(self.wav.read_bytes(), self.original)
        self.assertTrue(target.exists())

    def test_rename_existing_target_never_overwritten(self):
        mod = self.module('tag_studio')
        mod.simpledialog.askstring = Mock(return_value='{artist} - {title}')
        self.workspace.confirm_plan = lambda plan: True
        install('TagStudio', mod, self.workspace)
        target = self.path / 'LBR - NEW.wav'
        target.write_bytes(b'EXISTING TARGET')
        controller = SimpleNamespace(selected=lambda: [str(self.wav)], rows={str(self.wav): {'artist': 'LBR', 'title': 'NEW'}}, pending={}, backups=[], populate=Mock())
        with self.assertRaises(Conflict):
            mod.App.rename(controller)
        self.assertEqual(target.read_bytes(), b'EXISTING TARGET')
        self.assertEqual(self.wav.read_bytes(), self.original)


if __name__ == '__main__':
    unittest.main(verbosity=2)
