"""Additional isolated invariants; audio adapters are memory-only, no music writes."""
import sys,os,tempfile,unittest,importlib.util,base64,struct
from pathlib import Path
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1];NEW=ROOT/'Sources_application';BASE=ROOT/'Reference_PERFORMANCE_1'
if not BASE.exists():BASE=ROOT.parent/'p1/LBR_DJ_Library_Manager_RC2_PERFORMANCE_1/Sources_application'
tmp=tempfile.TemporaryDirectory(prefix='lbr_P2_tests_')
for k in ('HOME','USERPROFILE','APPDATA','LOCALAPPDATA'):os.environ[k]=tmp.name
sys.path[:0]=[str(NEW),str(NEW/'modules')]
def module(root,name,label):
 spec=importlib.util.spec_from_file_location(label,root/'modules'/name);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
old=module(BASE,'rekordbox_serato_v1_4.py','p1_serato');new=module(NEW,'rekordbox_serato_v1_4.py','p2_serato')
import tag_engine
from mutagen.id3 import ID3,TXXX,APIC
class Checks(unittest.TestCase):
 def test_only_presentation_file_changed(self):
  for p in BASE.rglob('*.py'):
   if p.name not in {'design_system.py','LBR_DJ_Library_Manager_FINAL.py'}:
    reference=ROOT/'Reference_FINAL/modules'/p.name if p.name=='rekordsync_v5_0_6.py' and (ROOT/'Reference_FINAL').exists() else p
    actual=(NEW/p.relative_to(BASE)).read_text(encoding='utf-8')
    if p.name=='task_hub.py':
     # The sole TaskHub extension finalizes large backup hashes on the worker.
     # Removing precisely that additive hook must yield the reference verbatim.
     actual=actual.replace(';self.listeners=[];self.finalizers=[]',';self.listeners=[]')
     actual=actual.replace("            for callback in self.finalizers:\n                try:callback(failure)\n                except Exception:failure=(failure or '')+'\\n'+traceback.format_exc()\n",'')
    self.assertEqual(reference.read_text(encoding='utf-8'),actual,str(p))
 def test_crate_unicode_wav_roundtrip(self):
  paths=['C:/Fictif/Été Réunion.wav','D:/Fictif/Autre.flac'];data=new.make_crate(paths)
  self.assertEqual(data,old.make_crate(paths))
  p=Path(tmp.name)/'demo.crate';p.write_bytes(data)
  self.assertEqual(new.read_crate_paths(p),['Fictif/Été Réunion.wav','Fictif/Autre.flac'])
 def test_xml_playlists_cues_loops(self):
  p=Path(tmp.name)/'demo.xml';p.write_text('''<DJ_PLAYLISTS><COLLECTION><TRACK TrackID="1" Location="file://localhost/C:/Fictif/Titre.wav"><POSITION_MARK Type="0" Num="1" Start="12.5" Name="Départ" Red="10" Green="20" Blue="30"/><POSITION_MARK Type="4" Num="-1" Start="16" End="24" Name="Boucle"/></TRACK></COLLECTION><PLAYLISTS><NODE Name="ROOT" Type="0"><NODE Name="Été" Type="1" KeyType="0"><TRACK Key="1"/></NODE></NODE></PLAYLISTS></DJ_PLAYLISTS>''',encoding='utf-8')
  roots,pls,n=new.parse_rekordbox_xml(p);self.assertEqual(n,1);self.assertEqual(pls[0].name,'Été');self.assertEqual(len(pls[0].tracks),1)
  self.assertEqual(new.parse_markers_by_path(p),old.parse_markers_by_path(p))
  markers=next(iter(new.parse_markers_by_path(p).values()))
  self.assertEqual(markers['cues'][0]['seconds'],12.5);self.assertEqual(markers['loops'][0]['end'],24)
  self.assertEqual(new.markers2_blob(**markers),old.markers2_blob(**markers))
 def test_marker_binary_values(self):
  cues=[dict(index=1,seconds=12.5,rgb=(10,20,30),name='Départ')];loops=[dict(index=0,start=16,end=24,rgb=(39,170,225),name='Boucle')]
  encoded=new.markers2_blob(cues,loops);self.assertEqual(encoded,old.markers2_blob(cues,loops))
  raw=base64.b64decode(encoded[2:].rstrip(b'\x00'))
  self.assertIn(struct.pack('>I',12500),raw);self.assertIn(struct.pack('>I',24000),raw);self.assertIn(b'LOOP\x00',raw)
 def test_wav_marker_rejected_without_write_and_warning_preserved(self):
  with self.assertRaisesRegex(RuntimeError,'non pris en charge'):new.inject_serato_markers(str(Path(tmp.name)/'absent.wav'),[],[])
  self.assertFalse((Path(tmp.name)/'absent.wav').exists())
  text=(NEW/'dashboard.py').read_text(encoding='utf-8');self.assertIn('Les WAV fonctionnent dans les crates Serato.',text);self.assertIn('Hot Cues / Saved Loops WAV sont ignorés.',text)
 def test_metadata_and_cover_in_memory(self):
  tags=ID3();tags.add(TXXX(encoding=3,desc='Serato Markers2',text=['OPAQUE_PRESERVE']));tags.add(APIC(encoding=3,mime='image/png',type=3,desc='Cover',data=b'OLD'))
  fake=Mock(tags=tags)
  with patch.object(tag_engine,'File',return_value=fake):
   tag_engine.write_tags('memory.mp3',{'title':'Été Réunion','artist':'LBR','comment':'Fictif'})
   self.assertEqual(tag_engine.read_tags('memory.mp3')['title'],'Été Réunion')
   self.assertEqual(tag_engine.read_cover('memory.mp3'),b'OLD')
   tag_engine.write_cover('memory.mp3',b'FAKE_PNG','image/png');self.assertEqual(tag_engine.read_cover('memory.mp3'),b'FAKE_PNG')
   self.assertEqual(str(tags.getall('TXXX')[0]),'OPAQUE_PRESERVE')
   tag_engine.write_cover('memory.mp3',None,'image/png');self.assertIsNone(tag_engine.read_cover('memory.mp3'))
 def test_safe_write_restores_dummy_on_validation_error(self):
  p=Path(tmp.name)/'dummy.dat';p.write_bytes(b'ORIGINAL_FICTIF')
  def broken(*args):p.write_bytes(b'CHANGED');raise RuntimeError('synthetic failure')
  with patch.object(tag_engine,'write_tags',side_effect=broken):
   with self.assertRaises(RuntimeError):tag_engine.safe_write(str(p),{},Path(tmp.name)/'backups')
  self.assertEqual(p.read_bytes(),b'ORIGINAL_FICTIF')
if __name__=='__main__':unittest.main(verbosity=2)
