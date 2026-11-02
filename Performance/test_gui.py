"""Actual Tk integration checks; synthetic rows, isolated settings and no DJ IO."""
import sys,os,tempfile,time,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];source=root/'Sources_application'
tmp=tempfile.TemporaryDirectory(prefix='lbr_gui_test_')
for key in ('HOME','USERPROFILE','APPDATA','LOCALAPPDATA'):os.environ[key]=tmp.name
sys.path[:0]=[str(source),str(source/'modules')]
import rekordsync_v5_0_6 as rb,rekordbox_serato_v1_4 as serato,tag_studio
rb.rbsync_python=lambda:None;serato.find_serato_roots=lambda:[];tag_studio.read_cover=lambda p:None
from LBR_DJ_Library_Manager_FINAL import LBRManager
app=LBRManager();errors=[];checks=[]
app.report_callback_exception=lambda *e:errors.append(str(e));app.report_task_error=lambda *e:errors.append(str(e))
def settle():
 deadline=time.perf_counter()+30
 def poll():
  if time.perf_counter()>deadline:errors.append('timeout');app.quit();return
  a=app.apps.get('TagStudio')
  if app.hub.busy or app.hub.deferred or not app.hub.messages.empty() or (a and a._populate_job) or app.dashboard._job:app.after(1,poll)
  else:app.after_idle(app.quit)
 app.after(0,poll);app.mainloop();app.update_idletasks()
def check(name,condition):
 if not condition:raise AssertionError(name)
 checks.append(name)
try:
 for page in app.nav:app.show_page(page);settle()
 check('all_four_controllers_open',set(app.apps)==set(app.engines))
 identities={k:id(v) for k,v in app.pages.items()}
 for _ in range(3):
  for page in app.nav:app.show_page(page);settle()
 check('pages_reused',identities=={k:id(v) for k,v in app.pages.items()})
 for mode in ('clair','sombre','clair'):
  app.set_theme(mode);settle()
  for page in app.nav:
   app.show_page(page);settle()
   stack=[app.pages[page]]
   while stack:
    w=stack.pop();stack.extend(w.children.values())
    base=getattr(w,'_lbr_base_style',None)
    if base in app._style_names:
     check_name='palette_'+mode+'_'+str(w)
     assert str(w.cget('style'))==mode+'.'+base,check_name
 checks.append('visible_and_hidden_pages_follow_palette')
 app.show_page('TagStudio');settle();a=app.apps['TagStudio'];a.folder=tmp.name
 a.rows={str(Path(tmp.name)/f'folder{i%10}'/f'{i}.flac'):{'title':f'Titre {i}','artist':'LÉA CHURROS','path':str(Path(tmp.name)/f'folder{i%10}'/f'{i}.flac')} for i in range(10000)}
 heartbeat=[]
 def tick():heartbeat.append(time.perf_counter());app.after(10,tick)
 app.after(10,tick);a.populate();app.show_page('MusicGenre');app.set_theme('sombre');settle()
 check('10000_rows_loaded',len(a.tree.get_children())==10000)
 check('navigation_during_population',app.current=='MusicGenre')
 check('heartbeat_during_load',len(heartbeat)>2)
 app.show_page('TagStudio');settle();p=next(iter(a.rows));a.tree.selection_set(p);settle()
 a.pending[p]={'title':'MODIFIÉ'};a.populate();settle()
 check('pending_row_value',a.tree.item(p,'values')[1]=='MODIFIÉ')
 check('editor_updates_on_mutation',a.edit_vars['title'].get()=='MODIFIÉ')
 a.search.set('modifié');settle();check('filtered_pending_edit',a.tree.get_children()==(p,))
 a.pending.clear();a.populate();settle();check('invalidated_search_after_clear',not a.tree.get_children())
 a.search.set('');settle();check('all_rows_restored',len(a.tree.get_children())==10000)
 # A newly created editor is registered through Map and recolored on next switch.
 from tkinter import ttk
 entry=ttk.Entry(a.tree);entry.place(x=0,y=0);settle()
 check('new_widget_palette',entry.cget('style')==app.mode+'.TEntry')
 app.set_theme('clair');settle();check('dynamic_widget_palette_change',entry.cget('style')=='clair.TEntry');entry.destroy()
 check('no_callback_or_worker_errors',not errors)
finally:
 if not app.hub.busy:app.hub.shutdown();app.destroy()
result={'passed':len(checks),'checks':checks,'errors':errors,'platform':sys.platform}
(root/'Performance/gui_tests.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
