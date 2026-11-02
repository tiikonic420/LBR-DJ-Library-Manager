"""Real Tk keyboard/programmatic focus tests, isolated fictitious data only."""
import os,sys,tempfile,time,unittest,types,threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk
ROOT=Path(__file__).resolve().parents[1];scratch=tempfile.TemporaryDirectory(prefix='lbr_focus_r8_')
for key in ('HOME','USERPROFILE','APPDATA','LOCALAPPDATA'):os.environ[key]=scratch.name
sys.path[:0]=[str(ROOT/'Sources_application'),str(ROOT/'Sources_application/modules')]
import rekordsync_v5_0_6 as rb,rekordbox_serato_v1_4 as se,tag_studio as tag
rb.rbsync_python=lambda:None;se.find_serato_roots=lambda:[];tag.read_cover=lambda _:None
from LBR_DJ_Library_Manager_FINAL import LBRManager
class PageFocus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=LBRManager();cls.errors=[]
        cls.app.geometry(f'{min(1280,cls.app.winfo_screenwidth()-80)}x{min(800,cls.app.winfo_screenheight()-100)}+20+20')
        cls.app.attributes('-topmost',True)
        cls.app.report_callback_exception=lambda *x:cls.errors.append(str(x))
        cls.app.report_task_error=lambda *x:cls.errors.append(str(x))
        for key in cls.app.nav:cls.app.show_page(key);cls.flush()
    @classmethod
    def flush(cls):
        end=time.perf_counter()+20
        def poll():
            a=cls.app;t=a.apps.get('TagStudio')
            if a.hub.busy or a.hub.deferred or not a.hub.messages.empty() or (t and t._populate_job) or a.dashboard._job:
                if time.perf_counter()>end:cls.errors.append('timeout');a.quit()
                else:a.after(1,poll)
            else:a.after_idle(a.quit)
        cls.app.after(0,poll);cls.app.mainloop();cls.app.update_idletasks();cls.app.update()
    def setUp(self):
        self.app.show_page('Accueil');self.app.lift();self.app.focus_force();self.app.nav['Accueil'].focus_force();self.flush()
    def tearDown(self):self.assertEqual(self.errors,[])
    @classmethod
    def tearDownClass(cls):
        cls.flush()
        assert not cls.app.hub.busy and not cls.app.hub.deferred
        assert cls.app.hub.shutdown();cls.app.destroy();assert not cls.errors,cls.errors
    def eligible(self,w):return self.app.tk.getboolean(self.app.tk.call('::lbrPageFocus::eligible',str(w)))
    def cycle(self,direction):
        current=str(self.app.nav[self.app.current]);seen=[]
        for _ in range(1000):
            nxt=str(self.app.tk.call(direction,current))
            if nxt in seen:return seen
            seen.append(nxt);current=nxt
        self.fail('Unbounded focus cycle')
    def test_forward_cycle_excludes_all_inactive_pages(self):
        for key in self.app.nav:
            self.app.show_page(key);self.flush();cycle=self.cycle('tk_focusNext');self.assertTrue(cycle)
            self.assertTrue(all(self.eligible(w) for w in cycle),(key,cycle))
    def test_reverse_cycle_excludes_all_inactive_pages(self):
        for key in self.app.nav:
            self.app.show_page(key);self.flush();cycle=self.cycle('tk_focusPrev');self.assertTrue(cycle)
            self.assertTrue(all(self.eligible(w) for w in cycle),(key,cycle))
    def test_real_tab_and_shift_tab_do_not_enter_hidden_page(self):
        for sequence in ('<Tab>','<Shift-Tab>'):
            for _ in range(35):
                w=self.app.focus_get();self.assertIsNotNone(w);w.event_generate(sequence);self.flush()
                self.assertTrue(self.eligible(self.app.focus_get()))
    def test_hidden_programmatic_focus_is_blocked(self):
        w=ttk.Entry(self.app.apps['TagStudio'].tree);w.place(x=2,y=2,width=80,height=24);self.flush()
        try:
            self.assertTrue(w.winfo_ismapped());self.assertFalse(self.eligible(w))
            original=self.app.focus_get();w.focus_set();self.flush();self.assertIs(self.app.focus_get(),original)
            w.focus_force();self.flush();self.assertIs(self.app.focus_get(),original)
        finally:w.destroy();self.flush()
    def test_native_focus_in_guard_recovers_valid_focus(self):
        w=ttk.Entry(self.app.apps['TagStudio'].tree);w.place(x=2,y=2,width=80,height=24);self.flush()
        try:
            self.app.tk.call('::lbrPageFocus::nativeFocus','-force',str(w));self.flush()
            self.assertIsNot(self.app.focus_get(),w);self.assertTrue(self.eligible(self.app.focus_get()))
        finally:w.destroy();self.flush()
    def test_active_widget_focus_and_original_takefocus_are_preserved(self):
        self.app.show_page('TagStudio');self.flush();w=ttk.Entry(self.app.apps['TagStudio'].tree,takefocus=1);w.place(x=2,y=2,width=80,height=24);self.flush()
        try:
            w.focus_force();self.flush();self.assertIs(self.app.focus_get(),w)
            self.app.show_page('Accueil');self.flush();self.assertTrue(self.eligible(self.app.focus_get()))
            self.assertEqual(str(w.cget('takefocus')),'1')
            self.app.show_page('TagStudio');self.flush();self.assertTrue(self.app.tk.getboolean(self.app.tk.call('tk::FocusOK',str(w))))
            self.assertEqual(str(w.cget('takefocus')),'1')
        finally:w.destroy();self.flush()
    def test_dynamic_hidden_widget_recreation_and_unicode_path(self):
        parent=self.app.apps['TagStudio'].tree;w=ttk.Entry(parent,name='x_été espace',takefocus=1);w.place(x=2,y=2,width=80,height=24);self.flush();path=str(w)
        self.assertFalse(self.eligible(w));w.destroy();self.flush()
        w=ttk.Entry(parent,name='x_été espace',takefocus=1);w.place(x=2,y=2,width=80,height=24);self.flush()
        try:
            self.assertEqual(str(w),path);self.assertFalse(self.app.tk.getboolean(self.app.tk.call('tk::FocusOK',str(w))))
            self.app.show_page('TagStudio');self.flush();self.assertTrue(self.app.tk.getboolean(self.app.tk.call('tk::FocusOK',str(w))))
        finally:w.destroy();self.flush()
    def test_custom_takefocus_and_disabled_state_delegate_to_native(self):
        called=[];command=self.app.register(lambda w:called.append(w) or 1)
        w=ttk.Entry(self.app.side,takefocus=command);w.pack();disabled=ttk.Entry(self.app.side,state='disabled');disabled.pack();self.flush()
        try:
            self.assertTrue(self.app.tk.getboolean(self.app.tk.call('tk::FocusOK',str(w))));self.assertIn(str(w),called)
            self.assertFalse(self.app.tk.getboolean(self.app.tk.call('tk::FocusOK',str(disabled))))
        finally:w.destroy();disabled.destroy();self.app.deletecommand(command);self.flush()
    def test_focus_queries_clear_and_errors_keep_native_semantics(self):
        for args in ((),('-displayof',str(self.app)),('-lastfor',str(self.app))):
            self.assertEqual(self.app.tk.call('focus',*args),self.app.tk.call('::lbrPageFocus::nativeFocus',*args))
        for args in (('-unknown',),('.missing_focus_widget',),('-force','.missing_focus_widget')):
            with self.assertRaises(tk.TclError):self.app.tk.call('focus',*args)
        self.app.tk.call('::lbrPageFocus::nativeFocus','');native_after=self.app.tk.call('::lbrPageFocus::nativeFocus')
        self.app.tk.call('focus','');self.assertEqual(self.app.tk.call('focus'),native_after)
        self.app.nav['Accueil'].focus_force();self.flush()
    def test_modal_top_level_focus_and_grab_survive_navigation(self):
        top=tk.Toplevel(self.app);w=ttk.Entry(top);w.pack();top.grab_set();w.focus_force();self.flush()
        try:
            self.app.show_page('MusicGenre');self.flush()
            self.assertIs(self.app.grab_current(),top);self.assertIs(self.app.focus_get(),w)
            self.assertTrue(self.app.tk.getboolean(self.app.tk.call('tk::FocusOK',str(w))))
        finally:top.grab_release();top.destroy();self.flush()
    def test_theme_resize_and_front_page_hit_testing(self):
        for mode in ('clair','sombre'):
            self.app.set_theme(mode)
            for key in self.app.nav:
                self.app.show_page(key);self.flush();page=self.app.pages[key]
                x=page.winfo_rootx()+page.winfo_width()//2;y=page.winfo_rooty()+page.winfo_height()//2
                hit=self.app.winfo_containing(x,y);self.assertIsNotNone(hit,(key,x,y,self.app.geometry(),self.app.winfo_screenwidth(),self.app.winfo_screenheight()))
                self.assertTrue(str(hit)==str(page) or str(hit).startswith(str(page)+'.'),(key,str(hit)))
                self.assertTrue(all(self.eligible(w) for w in self.cycle('tk_focusNext')))
        for geometry in ('1100x700','1440x900'):
            self.app.geometry(geometry);self.flush();self.assertTrue(all(self.eligible(w) for w in self.cycle('tk_focusPrev')))
    def test_inline_edit_commits_on_page_change_without_hidden_focus(self):
        self.app.show_page('TagStudio');self.flush();t=self.app.apps['TagStudio'];path='C:/Fictif/edition.flac'
        t.rows={path:{'path':path,'file':'edition.flac','title':'Avant','artist':'Fictif'}};t.populate();self.flush()
        box=t.tree.bbox(path,'title');self.assertTrue(box)
        x,y,w,h=box;t.edit_cell(types.SimpleNamespace(x=x+5,y=y+h//2));self.flush()
        entry=next(child for child in t.tree.winfo_children() if isinstance(child,ttk.Entry))
        entry.delete(0,'end');entry.insert(0,'Après fictif');entry.focus_force();self.flush()
        self.app.show_page('Accueil');self.flush()
        self.assertEqual(t.pending[path]['title'],'Après fictif');self.assertFalse(entry.winfo_exists())
        self.assertTrue(self.eligible(self.app.focus_get()));t.pending.clear()
    def test_background_focus_request_cannot_steal_from_active_page(self):
        w=ttk.Entry(self.app.apps['TagStudio'].tree);w.place(x=2,y=2,width=80,height=24);self.flush()
        try:
            self.app.hub.run('TagStudio','Test focus fictif',lambda:self.app.hub.ui(w.focus_force));self.flush()
            self.assertIsNot(self.app.focus_get(),w);self.assertTrue(self.eligible(self.app.focus_get()))
        finally:w.destroy();self.flush()
    def test_other_tk_interpreter_has_no_policy_override(self):
        other=tk.Tk();other.withdraw()
        try:
            self.assertFalse(other.tk.getboolean(other.tk.call('namespace','exists','::lbrPageFocus')))
            self.assertFalse(other.tk.call('info','procs','::focus'))
            self.assertTrue(self.app.tk.getboolean(self.app.tk.call('namespace','exists','::lbrPageFocus')))
        finally:other.destroy()
    def test_context_menu_focus_grab_and_command_delegate_normally(self):
        self.app.show_page('TagStudio');self.flush();calls=[]
        menu=tk.Menu(self.app.apps['TagStudio'].tree,tearoff=False)
        menu.add_command(label='Action fictive',command=lambda:calls.append('ok'))
        observed={};callback_errors=[];watchdog=None
        def exercise():
            try:
                observed['eligible']=self.eligible(menu)
                observed['query']=self.app.tk.call('focus','-displayof',str(menu))
                observed['native_query']=self.app.tk.call('::lbrPageFocus::nativeFocus','-displayof',str(menu))
                menu.invoke(0)
            except Exception as exc:callback_errors.append(repr(exc))
            finally:menu.unpost()
        # Windows posts a native blocking menu; arrange its action before posting.
        callback=self.app.after(100,exercise)
        if sys.platform=='win32':
            import ctypes
            user=ctypes.WinDLL('user32',use_last_error=True)
            user.GetWindowThreadProcessId.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32)]
            user.PostMessageW.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_size_t,ctypes.c_ssize_t]
            user.GetClassNameW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_int]
            enum_callback=ctypes.WINFUNCTYPE(ctypes.c_int,ctypes.c_void_p,ctypes.c_ssize_t)
            user.EnumThreadWindows.argtypes=[ctypes.c_uint32,enum_callback,ctypes.c_ssize_t]
            handles=[self.app.winfo_id(),int(self.app.tk.call('wm','frame',str(self.app)),16)]
            for handle in handles:
                owner=ctypes.c_uint32();thread_id=user.GetWindowThreadProcessId(handle,ctypes.byref(owner));self.assertEqual(owner.value,os.getpid())
            @enum_callback
            def close_own_native_menu(handle,_):
                owner=ctypes.c_uint32();user.GetWindowThreadProcessId(handle,ctypes.byref(owner))
                if owner.value==os.getpid():
                    name=ctypes.create_unicode_buffer(256);user.GetClassNameW(handle,name,len(name))
                    observed.setdefault('owned_window_classes',[]).append(name.value)
                    user.PostMessageW(handle,0x001F,0,0)
                    if name.value=='#32768':
                        user.PostMessageW(handle,0x0100,0x1B,1);user.PostMessageW(handle,0x0101,0x1B,1)
                return 1
            watchdog=threading.Timer(2,lambda:user.EnumThreadWindows(thread_id,close_own_native_menu,0))
            watchdog.daemon=True;watchdog.start()
        try:
            menu.post(self.app.winfo_rootx()+300,self.app.winfo_rooty()+200);self.flush()
            self.assertEqual(callback_errors,[]);self.assertTrue(observed.get('eligible'))
            self.assertEqual(observed['query'],observed['native_query']);self.assertEqual(calls,['ok'])
        finally:
            if watchdog:watchdog.cancel();watchdog.join()
            self.app.after_cancel(callback);menu.unpost();menu.destroy();self.flush()
if __name__=='__main__':unittest.main(verbosity=2)
