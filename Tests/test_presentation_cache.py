"""Real Tcl behavior, theme writes and cross-thread ordering of the UI cache."""
import sys,threading,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Sources_application'))
import tkinter as tk
from tkinter import ttk
from task_hub import TaskHub
from presentation_cache import cache_pending_foreground
class PresentationCache(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.root.withdraw();self.hub=TaskHub(self.root);self.tree=ttk.Treeview(self.root);self.calls=[]
        original=self.tree.tag_configure
        self.native_tag_configure=original
        def observe(tagname,option=None,**kw):
            self.calls.append((threading.get_ident(),tagname,option,dict(kw)))
            return original(tagname,option,**kw)
        self.tree.tag_configure=observe
        cache_pending_foreground(self.tree,self.hub)
    def tearDown(self):
        self.assertTrue(self.hub.shutdown());self.root.destroy()
    def writes(self):return [c for c in self.calls if c[2] is None and c[3] and all(v is not None for v in c[3].values())]
    def assert_tag_color(self,tagname,color,actual=None):
        if actual is None:actual=self.tree.tag_configure(tagname,'foreground')
        native=self.native_tag_configure(tagname,'foreground')
        # Tk 8.6 returns a Tcl color object, not necessarily a Python string.
        # Preserve its native type as well as the exact configured value.
        self.assertIs(type(actual),type(native))
        self.assertEqual(str(actual),color)
        self.assertEqual(str(native),color)
    def test_repeated_color_has_one_native_write_and_same_return(self):
        self.assertEqual(self.tree.tag_configure('pending',foreground='#00a876'),{})
        for _ in range(50):self.assertEqual(self.tree.tag_configure('pending',foreground='#00a876'),{})
        self.assertEqual(len(self.writes()),1)
        self.assert_tag_color('pending','#00a876')
    def test_theme_color_changes_are_applied_and_can_change_back(self):
        for color in ('#00a876','#101010','#00a876'):
            self.tree.tag_configure('pending',foreground=color)
            self.assert_tag_color('pending',color)
        self.assertEqual(len(self.writes()),3)
    def test_queries_none_and_other_tags_keep_tcl_semantics(self):
        self.tree.tag_configure('pending',foreground='red')
        self.assert_tag_color('pending','red',self.tree.tag_configure('pending',foreground=None))
        self.assertEqual(self.tree.tag_configure('pending'),self.native_tag_configure('pending'))
        self.assertEqual(self.tree.tag_configure('pending')['foreground'],'red')
        self.tree.tag_configure('other',foreground='blue')
        self.assert_tag_color('other','blue')
        self.assert_tag_color('pending','red')
    def test_other_pending_write_invalidates_cached_color(self):
        self.tree.tag_configure('pending',foreground='red')
        self.tree.tag_configure('pending',foreground='blue',background='white')
        self.tree.tag_configure('pending',foreground='red')
        self.assert_tag_color('pending','red')
        self.assertEqual(len(self.writes()),3)
    def test_failed_native_write_is_not_cached(self):
        self.tree.tag_configure('pending',foreground='red')
        for _ in range(2):
            with self.assertRaises(tk.TclError):self.tree.tag_configure('pending',foreground='not-a-color-lbr')
        self.assertEqual(len([c for c in self.calls if c[3].get('foreground')=='not-a-color-lbr']),2)
        self.assert_tag_color('pending','red')
    def test_install_is_idempotent(self):
        method=self.tree.tag_configure;cache_pending_foreground(self.tree,self.hub)
        self.assertIs(self.tree.tag_configure,method)
    def test_worker_write_and_ui_theme_have_consistent_order(self):
        self.tree.tag_configure('pending',foreground='red');errors=[]
        def work():
            try:self.tree.tag_configure('pending',foreground='blue')
            except Exception as e:errors.append(repr(e))
        worker=threading.Thread(target=work);worker.start();deadline=time.monotonic()+5
        while self.hub.messages.empty() and time.monotonic()<deadline:time.sleep(.001)
        self.assertFalse(self.hub.messages.empty())
        self.tree.tag_configure('pending',foreground='green')
        while worker.is_alive() and time.monotonic()<deadline:self.root.update();time.sleep(.001)
        worker.join(1);self.assertFalse(worker.is_alive());self.assertEqual(errors,[])
        self.assert_tag_color('pending','blue')
        n=len(self.writes());self.tree.tag_configure('pending',foreground='blue');self.assertEqual(len(self.writes()),n)
        self.assertTrue(all(c[0]==self.hub.ui_ident for c in self.calls))
if __name__=='__main__':unittest.main(verbosity=2)
