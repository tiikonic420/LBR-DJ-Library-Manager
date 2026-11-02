import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Sources_application'))
from reliability import BackupStore, Conflict, Cancelled, Journal, digest, preview, diagnose_rbsync


class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = BackupStore(self.root / 'backups')
        self.file = self.root / 'fictif.wav'
        self.file.write_bytes(b'ORIGINAL')

    def test_snapshot_verified_and_selective_restore(self):
        other = self.root / 'other.flac'
        other.write_bytes(b'OTHER')
        identifier = self.store.create([self.file, other])
        self.file.write_bytes(b'EDITED')
        other.write_bytes(b'EDITED OTHER')
        self.store.mark(identifier)
        self.assertEqual(self.store.restore(identifier, [self.file]), 1)
        self.assertEqual(self.file.read_bytes(), b'ORIGINAL')
        self.assertEqual(other.read_bytes(), b'EDITED OTHER')

    def test_corrupt_backup_refused_without_target_change(self):
        identifier = self.store.create([self.file])
        (self.store._folder(identifier) / '00000000.bin').write_bytes(b'CORRUPT')
        with self.assertRaises(Conflict):
            self.store.restore(identifier)
        self.assertEqual(self.file.read_bytes(), b'ORIGINAL')

    def test_external_change_conflict(self):
        identifier = self.store.create([self.file])
        self.file.write_bytes(b'EXTERNAL')
        with self.assertRaises(Conflict):
            self.store.restore(identifier)
        self.assertEqual(self.file.read_bytes(), b'EXTERNAL')

    def test_protected_failure_rolls_back(self):
        with self.assertRaisesRegex(RuntimeError, 'synthetic'):
            with self.store.protect([self.file]):
                self.file.write_bytes(b'PARTIAL')
                raise RuntimeError('synthetic')
        self.assertEqual(self.file.read_bytes(), b'ORIGINAL')

    def test_failed_mandatory_backup_blocks_writer(self):
        calls = []
        with patch('reliability.shutil.copy2', side_effect=PermissionError('synthetic ACL')):
            with self.assertRaises(PermissionError):
                with self.store.protect([self.file]):
                    calls.append('writer')
        self.assertEqual(calls, [])
        self.assertEqual(self.store.list(), [])

    def test_locked_restore_preserves_target(self):
        identifier = self.store.create([self.file])
        self.file.write_bytes(b'CURRENT')
        self.store.mark(identifier)
        original_replace = os.replace
        def locked(src, dst):
            if Path(dst) == self.file:
                raise PermissionError('locked by Windows simulation')
            return original_replace(src, dst)
        with patch('reliability.os.replace', side_effect=locked):
            with self.assertRaises(PermissionError):
                self.store.restore(identifier)
        self.assertEqual(self.file.read_bytes(), b'CURRENT')
        self.assertEqual(list(self.root.glob('.lbr-restore-*')), [])

    def test_changed_during_backup_refused(self):
        import shutil
        original_copy = shutil.copy2
        def race(src, dst):
            result = original_copy(src, dst)
            if Path(src) == self.file:
                self.file.write_bytes(b'RACE')
            return result
        with patch('reliability.shutil.copy2', side_effect=race):
            with self.assertRaises(Conflict):
                self.store.create([self.file])
        self.assertEqual(self.store.list(), [])

    def test_cancel_before_write(self):
        def cancel():
            raise Cancelled('synthetic')
        with self.assertRaises(Cancelled):
            with self.store.protect([self.file], checkpoint=cancel):
                self.fail('writer reached')
        self.assertEqual(self.file.read_bytes(), b'ORIGINAL')

    def test_no_automatic_deletion_of_created_file(self):
        target = self.root / 'created.m3u8'
        identifier = self.store.create([target])
        target.write_bytes(b'NEW')
        self.store.mark(identifier)
        with self.assertRaises(Conflict):
            self.store.restore(identifier)
        self.assertTrue(target.exists())

    def test_manifest_path_traversal_refused(self):
        with self.assertRaises(ValueError):
            self.store.load('../escape')
        identifier = self.store.create([self.file])
        p = self.store._folder(identifier) / 'manifest.json'
        data = json.loads(p.read_text())
        data['files'][0]['blob'] = '../other'
        p.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            self.store.verify(identifier)

    def test_partial_manifest_not_listed(self):
        p = self.store.root / ('a' * 32)
        p.mkdir()
        (p / '00000000.bin').write_bytes(b'PARTIAL')
        self.assertEqual(self.store.list(), [])

    def test_symlink_refused(self):
        p = self.root / 'link.wav'
        try:
            p.symlink_to(self.file)
        except OSError:
            self.skipTest('Symbolic links unavailable')
        with self.assertRaises(ValueError):
            self.store.create([p])

    def test_journal_recovery_and_export(self):
        path = self.root / 'tasks.sqlite'
        journal = Journal(path)
        identifier = journal.start('Synthetic', 'Interruption')
        journal.update(identifier, done=7, total=10)
        recovered = Journal(path)
        self.assertEqual(recovered.list()[0]['state'], 'interrupted')
        export = self.root / 'tasks.json'
        recovered.export(export)
        self.assertEqual(json.loads(export.read_text())['tasks'][0]['done'], 7)

    def test_preview_does_not_write(self):
        before = digest(self.file)
        value = preview('MusicGenre', [{'path': str(self.file), 'before': 'old', 'after': 'new'}])
        self.assertEqual(value['module'], 'MusicGenre')
        self.assertEqual(digest(self.file), before)
        self.assertEqual(self.store.list(), [])

    def test_diagnostic_only_allowed_commands_and_real_python_version(self):
        from types import SimpleNamespace
        commands = []
        def run(command, **kwargs):
            commands.append(command)
            text = json.dumps({'python': [3, 12, 10], 'rbsync': '0.2.0'}) if '-c' in command else 'Usage'
            return SimpleNamespace(returncode=0, stdout=text, stderr='')
        result = diagnose_rbsync([self.file], runner=run)
        self.assertFalse(result['candidates'][0]['compatible'])
        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[1][-3:], ['-m', 'rbsync', '--help'])
        self.assertFalse(any('pip' in str(c) for c in commands))


if __name__ == '__main__':
    unittest.main(verbosity=2)
