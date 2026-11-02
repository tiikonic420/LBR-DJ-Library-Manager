from pathlib import Path
import json
import sys
import tempfile
import unittest
import wave
from unittest.mock import patch
sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'Sources_application'), str(Path(__file__).resolve().parents[1] / 'Sources_application/modules')]
from library_services import Catalogue, authorized, audio_info, compile_rules, propose_paths, batch_plan, apply_batch, repair_xml, export_playlist
from reliability import BackupStore, Conflict, digest


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.music = self.root / 'music'
        self.music.mkdir()
        self.roots = [self.music]
        self.store = BackupStore(self.root / 'backups')
        self.catalogue = Catalogue(self.root / 'index.sqlite')
        self.wav = self.music / 'Été.wav'
        with wave.open(str(self.wav), 'wb') as stream:
            stream.setparams((2, 2, 44100, 0, 'NONE', 'not compressed'))
            stream.writeframes(b'\0' * 44100 * 4)

    def test_real_wav_quality(self):
        info = audio_info(self.wav)
        self.assertFalse(info['error'])
        self.assertEqual(info['sample_rate'], 44100)
        self.assertEqual(info['bits'], 16)
        self.assertEqual(info['channels'], 2)
        self.assertAlmostEqual(info['duration'], 1)

    def test_unreadable_audio_is_reported(self):
        bad = self.music / 'bad.mp3'
        bad.write_bytes(b'NOT AUDIO')
        self.assertTrue(audio_info(bad)['error'])

    def test_index_read_only_incremental_and_missing_retained(self):
        before = digest(self.wav)
        first = self.catalogue.index(self.roots)
        second = self.catalogue.index(self.roots)
        self.assertEqual(first['changed'], 1)
        self.assertEqual(second['unchanged'], 1)
        self.assertEqual(digest(self.wav), before)
        self.wav.unlink()
        self.catalogue.index(self.roots)
        self.assertEqual(self.catalogue.missing(self.roots), [str(self.wav)])

    def test_unicode_search_paging_and_filters(self):
        rows = [{'path': str(self.music / f'{i}.flac'), 'artist': 'LÉA Réunion', 'title': f'Titre {i}', 'year': 2026, 'bpm': 120 + i, 'key': '8A'} for i in range(12)]
        self.catalogue.upsert(rows)
        hits = self.catalogue.search('léa', {'bpm_min': 125, 'bpm_max': 129, 'key': '8A'}, page_size=2)
        self.assertEqual(len(hits), 2)
        self.assertTrue(all(125 <= r['bpm'] <= 129 for r in hits))
        self.assertEqual(len(self.catalogue.search('2026')), 12)
        self.assertEqual(len(self.catalogue.search("' OR 1=1 --")), 0)
        with self.assertRaises(ValueError):
            self.catalogue.search(filters={'unknown': 1})

    def test_exact_and_probable_duplicates_no_deletion(self):
        a, b, c = [self.music / n for n in ('a.mp3', 'b.mp3', 'c.mp3')]
        a.write_bytes(b'EXACT');b.write_bytes(b'EXACT');c.write_bytes(b'OTHER DATA')
        rows = [{'path': str(p), 'artist': 'ARTISTE', 'title': 'Titre', 'duration': d} for p, d in [(a, 60), (b, 60), (c, 61)]]
        self.catalogue.upsert(rows)
        result = self.catalogue.duplicates(self.roots)
        self.assertEqual(len(result['exact_sha256']), 1)
        self.assertTrue(result['probable'])
        self.assertEqual(result['deletions'], 0)
        self.assertTrue(all(p.exists() for p in (a, b, c)))

    def test_path_proposals_ambiguous_not_auto_applied(self):
        other = self.music / 'folder'
        other.mkdir()
        (other / self.wav.name).write_bytes(self.wav.read_bytes())
        result = propose_paths(['/old/' + self.wav.name], self.roots)
        self.assertEqual(len(result[0]['candidates']), 2)
        self.assertEqual(result[0]['confidence'], 'ambigu ou absent')

    def test_authorization_blocks_traversal_and_symlink_escape(self):
        with self.assertRaises(PermissionError):
            authorized(self.music / '../secret', self.roots)
        p = self.music / 'escape'
        try:
            p.symlink_to(self.root)
        except OSError:
            self.skipTest('Symbolic links unavailable; symlink escape not exercised')
        with self.assertRaises(PermissionError):
            authorized(p / 'secret', self.roots)

    def test_xml_repair_preserves_marker_values_and_source(self):
        import xml.etree.ElementTree as ET
        source = self.root / 'rekordbox.xml'
        source.write_text('<DJ_PLAYLISTS><COLLECTION><TRACK TrackID="1" Location="/missing/Été.wav" Artist="LBR"><POSITION_MARK Num="2" Start="12.5" End="24" Name="Boucle"/></TRACK></COLLECTION></DJ_PLAYLISTS>', encoding="utf-8")
        original = source.read_bytes()
        output = self.root / 'repaired.xml'
        result = repair_xml(source, {'/missing/Été.wav': str(self.wav)}, self.roots, self.store, output)
        self.assertEqual(len(result['changes']), 1)
        track = ET.parse(output).find('.//TRACK')
        self.assertEqual(track.attrib['Artist'], 'LBR')
        self.assertEqual(track.find('POSITION_MARK').attrib, {'Num': '2', 'Start': '12.5', 'End': '24', 'Name': 'Boucle'})
        self.assertEqual(source.read_bytes(), original)

    def test_smart_rules_and_export_after_snapshot(self):
        self.catalogue.upsert([{'path': str(self.wav), 'genre': 'Maloya', 'bpm': 125, 'year': 2026}])
        rules = {'mode': 'AND', 'rules': [{'field': 'genre', 'op': '=', 'value': 'Maloya'}, {'mode': 'OR', 'rules': [{'field': 'bpm', 'op': '>=', 'value': 120}, {'field': 'year', 'op': '<', 'value': 2000}]}]}
        self.assertEqual(len(self.catalogue.search(rules=rules)), 1)
        target = self.root / 'playlist.m3u8'
        target.write_text('OLD')
        result = export_playlist(self.catalogue, rules, target, self.roots, self.store)
        self.assertEqual(result['tracks'], 1)
        self.assertIn(str(self.wav), target.read_text(encoding="utf-8"))
        self.assertEqual(len(self.store.list()), 1)
        with self.assertRaises(ValueError):
            compile_rules({'field': 'path); DROP TABLE tracks;', 'op': '=', 'value': ''})

    def test_batch_metadata_preserves_other_fields_and_undo(self):
        import tag_engine
        tag_engine.write_tags(str(self.wav), {'title': '  ÉTÉ  ', 'artist': 'LBR', 'comment': 'CONSERVER'})
        plan = batch_plan([self.wav], [{'field': 'title', 'action': 'normalize'}], self.roots)
        self.assertEqual(plan['changes'][0]['after'], {'title': 'ÉTÉ'})
        original = self.wav.read_bytes()
        identifier = apply_batch(plan, self.roots, self.store)
        tags = tag_engine.read_tags(str(self.wav))
        self.assertEqual(tags['title'], 'ÉTÉ')
        self.assertEqual(tags['comment'], 'CONSERVER')
        self.store.restore(identifier)
        self.assertEqual(self.wav.read_bytes(), original)

    def test_batch_obsolete_preview_refused(self):
        import tag_engine
        tag_engine.write_tags(str(self.wav), {'title': 'OLD'})
        plan = batch_plan([self.wav], [{'field': 'title', 'action': 'set', 'value': 'NEW'}], self.roots)
        tag_engine.write_tags(str(self.wav), {'comment': 'EXTERNAL'})
        with self.assertRaises(Conflict):
            apply_batch(plan, self.roots, self.store)
        self.assertEqual(tag_engine.read_tags(str(self.wav))['title'], 'OLD')

    def test_batch_regex_filename_replace_templates(self):
        import tag_engine
        p = self.music / 'LBR - Live.wav'
        p.write_bytes(self.wav.read_bytes())
        tag_engine.write_tags(str(p), {'title': 'Live 2026'})
        for transform, expected in [({'action': 'regex', 'search': r'\d+', 'replacement': '2027'}, 'Live 2027'), ({'action': 'replace', 'search': 'Live', 'replacement': 'Set'}, 'Set 2026'), ({'action': 'filename', 'pattern': '{artist} - {title}'}, 'Live')]:
            plan = batch_plan([p], [dict(field='title', **transform)], self.roots)
            self.assertEqual(plan['changes'][0]['after']['title'], expected)

    def test_regex_timeout_and_invalid_pattern(self):
        from library_services import bounded_regex
        with self.assertRaisesRegex(ValueError, 'trop coûteuse'):
            bounded_regex('(a+)+$', '', 'a' * 32 + '!')
        with self.assertRaisesRegex(ValueError, 'invalide'):
            bounded_regex('(', '', 'text')

    def test_xml_non_xml_destination_refused(self):
        source = self.root / 'source.xml'
        source.write_text('<DJ_PLAYLISTS/>')
        before = self.wav.read_bytes()
        with self.assertRaises(ValueError):
            repair_xml(source, {}, self.roots, self.store, self.wav)
        self.assertEqual(self.wav.read_bytes(), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
