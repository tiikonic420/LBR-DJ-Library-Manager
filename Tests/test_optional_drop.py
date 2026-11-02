"""Optional workspace and real WM_DROPFILES; synthetic audio only."""
import ctypes,hashlib,os,struct,sys,tempfile,time,unittest,wave
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
scratch=tempfile.TemporaryDirectory(prefix='lbr_optional_drop_')
for key in ('HOME','USERPROFILE','APPDATA','LOCALAPPDATA'):os.environ[key]=scratch.name
os.environ.pop('LBR_TEST_MODE',None)  # Exercise actual first-use startup.
sys.path[:0]=[str(ROOT/'Sources_application'),str(ROOT/'Sources_application/modules')]
import rekordsync_v5_0_6 as rb,rekordbox_serato_v1_4 as se
rb.rbsync_python=lambda:None;se.find_serato_roots=lambda:[]
from LBR_DJ_Library_Manager_FINAL import LBRManager
from file_drop import audio_paths

class OptionalDrop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=LBRManager();cls.errors=[]
        cls.app.report_callback_exception=lambda *a:cls.errors.append(str(a))
        cls.app.report_task_error=lambda *a:cls.errors.append(str(a))
        cls.flush();assert cls.app.workspace.window is None
        cls.app.show_page('TagStudio');cls.flush();cls.tag=cls.app.apps['TagStudio']
        cls.music=Path(scratch.name)/'Fictif été avec espaces';cls.music.mkdir()
        for name in ('A.wav','B.wav'):
            with wave.open(str(cls.music/name),'wb') as f:
                f.setparams((2,2,44100,0,'NONE','none'));f.writeframes(b'\0'*4410*4)
        (cls.music/'ignore.txt').write_text('fictif')
        cls.hashes={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in cls.music.glob('*.wav')}
    @classmethod
    def flush(cls):
        deadline=time.monotonic()+20
        quiet_since=None
        def poll():
            nonlocal quiet_since
            if time.monotonic()>deadline:cls.errors.append('timeout');cls.app.quit();return
            tag=cls.app.apps.get('TagStudio')
            pending=tag and hasattr(tag,'file_drop') and not tag.file_drop.pending.empty()
            if cls.app.hub.busy or cls.app.hub.deferred or not cls.app.hub.messages.empty() or pending:
                quiet_since=None;cls.app.after(2,poll)
            elif quiet_since is None:
                quiet_since=time.monotonic();cls.app.after(10,poll)
            elif time.monotonic()-quiet_since>=.12:cls.app.quit()
            else:cls.app.after(10,poll)
        cls.app.after(0,poll);cls.app.mainloop();cls.app.update()
    def setUp(self):self.app.show_page('TagStudio');self.flush()
    def tearDown(self):self.flush();self.assertEqual(self.errors,[])
    @classmethod
    def tearDownClass(cls):
        assert cls.app.hub.shutdown();cls.app.destroy()
    def test_01_startup_without_test_mode_does_not_open_workspace(self):
        self.assertIsNone(self.app.workspace.window)
        self.assertFalse(self.app.workspace.config.get('onboarded',False))
    def test_02_basic_and_advanced_tools_remain_available(self):
        w=self.app.workspace;w.open();self.flush()
        visible=lambda:[name for name,frame in w.tabs.items() if w.notebook.tab(frame,'state')!='hidden']
        self.assertEqual(visible(),['Accueil','Dossiers','Sauvegardes','Tâches'])
        self.assertTrue(w.backup_tree.winfo_exists())
        w.toggle_advanced();self.assertEqual(len(visible()),9)
        w.toggle_advanced();self.assertEqual(len(visible()),4)
        w.window.event_generate('<<Noop>>');w.window.destroy();w.window=None;self.flush()
        self.assertIsNotNone(w.journal);self.assertIsNotNone(w.store)
    def test_03_native_drop_reads_only_explicit_audio_and_keeps_pending(self):
        a=str(self.music/'A.wav');b=str(self.music/'B.wav')
        self.tag.rows[a]={'path':a,'file':'A.wav','title':'Existing'}
        self.tag.pending[a]={'title':'Non enregistré'}
        data=struct.pack('<IiiII',20,0,0,0,1)+(str(self.music)+'\0'+a+'\0\0').encode('utf-16le')
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GlobalAlloc.argtypes=[ctypes.c_uint,ctypes.c_size_t];kernel.GlobalAlloc.restype=ctypes.c_void_p
        kernel.GlobalLock.argtypes=[ctypes.c_void_p];kernel.GlobalLock.restype=ctypes.c_void_p
        kernel.GlobalUnlock.argtypes=[ctypes.c_void_p]
        memory=kernel.GlobalAlloc(0x42,len(data));self.assertTrue(memory)
        ptr=kernel.GlobalLock(memory);self.assertTrue(ptr);ctypes.memmove(ptr,data,len(data));kernel.GlobalUnlock(memory)
        user=ctypes.WinDLL('user32');user.SendMessageW.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_ssize_t];user.SendMessageW.restype=ctypes.c_ssize_t
        self.assertEqual(user.SendMessageW(self.tag.tree.winfo_id(),0x233,memory,0),0)
        self.flush()
        self.assertEqual(set(self.tag.rows),{a,b})
        self.assertEqual(self.tag.pending[a],{'title':'Non enregistré'})
        self.assertEqual(self.tag.rows[a]['title'],'Existing')
        self.assertEqual(len(self.tag.tree.get_children()),2)
        for p,digest in self.hashes.items():self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),digest)
        self.assertTrue(any(t['title']=='Lecture des fichiers déposés' and t['state']=='completed' for t in self.app.workspace.journal.list()))
    def test_04_hidden_page_and_busy_drop_are_refused(self):
        self.app.show_page('Accueil');self.assertFalse(self.tag.file_drop.receive([str(self.music)]))
        self.app.show_page('TagStudio')
        with patch.object(self.app.hub,'busy',True):self.assertFalse(self.tag.file_drop.receive([str(self.music)]))
    def test_05_paths_deduplicate_and_ignore_non_audio(self):
        calls=[];paths=audio_paths([str(self.music),str(self.music/'A.wav')],{'.wav'},lambda:calls.append(1))
        self.assertEqual(len(paths),2);self.assertTrue(calls)
    def test_06_relative_network_missing_and_cancel_are_rejected(self):
        for raw in ('relative.wav',r'\\server\share\song.wav',str(self.music/'missing.wav')):
            with self.assertRaises((ValueError,FileNotFoundError)):audio_paths([raw],{'.wav'},lambda:None)
        def cancel():raise RuntimeError('cancelled')
        with self.assertRaisesRegex(RuntimeError,'cancelled'):audio_paths([str(self.music)],{'.wav'},cancel)
    def test_07_safety_writes_still_back_up_with_workspace_closed(self):
        import tag_studio as tag
        path=self.music/'B.wav';before=path.read_bytes()
        backup_dir=Path(scratch.name)/'synthetic_legacy_backup';backup_dir.mkdir(exist_ok=True)
        self.app.hub.run('TagStudio','Synthetic protected tag write',lambda:tag.safe_write(str(path),{'title':'Fictif sauvegardé'},str(backup_dir)))
        self.flush();self.assertEqual(tag.read_tags(str(path))['title'],'Fictif sauvegardé')
        store=self.app.workspace.store;rows=store.list();self.assertTrue(rows)
        self.assertTrue(any(item['path']==str(path) for r in rows for item in store.verify(r['id'])['files']))
        self.assertNotEqual(path.read_bytes(),before)
    def test_08_native_subclass_lifetime_survives_theme_navigation(self):
        self.assertEqual(len(self.tag.file_drop.windows),3)
        for mode in ('clair','sombre'):
            self.app.set_theme(mode);self.app.show_page('Accueil');self.app.show_page('TagStudio');self.flush()
            self.assertEqual(len(self.tag.file_drop.windows),3)
    def test_09_windows_path_case_does_not_duplicate_existing_tracks(self):
        before=set(self.tag.rows)
        self.assertTrue(self.tag.file_drop.receive([str(self.music/'A.wav').swapcase()]))
        self.flush();self.assertEqual(set(self.tag.rows),before)
    def test_10_cancelled_drop_is_journalled_without_partial_import_or_error(self):
        import tag_studio as tag
        folder=Path(scratch.name)/'Dépôt annulé';folder.mkdir()
        for name in ('C.wav','D.wav'):
            with wave.open(str(folder/name),'wb') as f:
                f.setparams((1,2,44100,0,'NONE','none'));f.writeframes(b'\0'*882)
        original=tag.read_tags;before=set(self.tag.rows)
        def cancel_after_read(path):
            data=original(path);self.app.workspace.cancel.set();return data
        with patch.object(tag,'read_tags',side_effect=cancel_after_read):
            self.assertTrue(self.tag.file_drop.receive([str(folder)]));self.flush()
        self.assertEqual(set(self.tag.rows),before)
        rows=[r for r in self.app.workspace.journal.list() if r['title']=='Lecture des fichiers déposés']
        self.assertEqual(rows[0]['state'],'cancelled')
        self.assertEqual(self.errors,[])
    def test_11_native_queued_drop_during_mainloop(self):
        path=Path(scratch.name)/'Message Windows été.wav'
        with wave.open(str(path),'wb') as f:
            f.setparams((1,2,44100,0,'NONE','none'));f.writeframes(b'\0'*882)
        before=hashlib.sha256(path.read_bytes()).hexdigest();rows=set(self.tag.rows)
        data=struct.pack('<IiiII',20,0,0,0,1)+(str(path)+'\0\0').encode('utf-16le')
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GlobalAlloc.argtypes=[ctypes.c_uint,ctypes.c_size_t];kernel.GlobalAlloc.restype=ctypes.c_void_p
        kernel.GlobalLock.argtypes=[ctypes.c_void_p];kernel.GlobalLock.restype=ctypes.c_void_p
        kernel.GlobalUnlock.argtypes=[ctypes.c_void_p]
        memory=kernel.GlobalAlloc(0x42,len(data));self.assertTrue(memory)
        ptr=kernel.GlobalLock(memory);self.assertTrue(ptr);ctypes.memmove(ptr,data,len(data));kernel.GlobalUnlock(memory)
        user=ctypes.WinDLL('user32');user.PostMessageW.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_ssize_t];user.PostMessageW.restype=ctypes.c_int
        self.assertEqual(user.PostMessageW(self.tag.tree.winfo_id(),0x233,memory,0),1)
        self.flush()
        self.assertEqual(set(self.tag.rows),rows|{str(path)})
        self.assertIn(str(path),self.tag.tree.get_children())
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)

if __name__=='__main__':unittest.main(verbosity=2)
