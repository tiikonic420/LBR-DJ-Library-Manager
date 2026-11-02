"""Lifecycle / responsiveness regressions using real Tk and synthetic rows only."""
import sys,os,tempfile,time,threading,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];source=root/'Sources_application'
sys.dont_write_bytecode=True
tmp=tempfile.TemporaryDirectory(prefix='lbr_p2_gui_')
for key in ('HOME','USERPROFILE','APPDATA','LOCALAPPDATA'):os.environ[key]=tmp.name
sys.path[:0]=[str(source),str(source/'modules')]
import rekordsync_v5_0_6 as rb,rekordbox_serato_v1_4 as se,tag_studio as tag
rb.rbsync_python=lambda:None;se.find_serato_roots=lambda:[];tag.read_cover=lambda _:None
from LBR_DJ_Library_Manager_FINAL import LBRManager
app=LBRManager();errors=[];checks=[]
app.report_callback_exception=lambda *e:errors.append(str(e));app.report_task_error=lambda *e:errors.append(str(e))
def settle():
 deadline=time.perf_counter()+90
 def poll():
  if time.perf_counter()>deadline:errors.append('TIMEOUT');app.quit();return
  t=app.apps.get('TagStudio')
  if app.hub.busy or app.hub.deferred or not app.hub.messages.empty() or (t and t._populate_job) or app.dashboard._job:app.after(1,poll)
  else:app.after_idle(app.quit)
 app.after(0,poll);app.mainloop();app.update_idletasks();app.update()
def check(name,value):
 assert value,name
 checks.append(name);print(name,flush=True)
for page in app.nav:app.show_page(page);settle()
app.after(1200,app.quit);app.mainloop();settle()
ids={k:id(v) for k,v in app.pages.items()};pictures=set(app.skin.images)
for _ in range(4):
 for page in app.nav:
  app.show_page(page);app.set_theme('clair' if app.mode=='sombre' else 'sombre');settle()
check('page_identity_after_28_theme_navigation_cycles',ids=={k:id(v) for k,v in app.pages.items()})
check('patch_cache_bounded_across_themes',set(app.skin.images)==pictures)
check('patch_tile_dimension_bound',all(im.width()<=100 and im.height()<=100 for im in app.skin.images.values()))
app.show_page('TagStudio');settle();t=app.apps['TagStudio'];t.folder=tmp.name
paths=[str(Path(tmp.name)/f'g{i%20}'/f'{i}.flac') for i in range(50000)]
t.rows={p:{'path':p,'file':Path(p).name,'title':f'Titre {i}','artist':f'Artiste {i%100}'} for i,p in enumerate(paths)}
t.populate();check('shutdown_refused_while_task_active',not app.hub.shutdown())
app.show_page('Serato');app.set_theme('clair');t.search.set('artiste 12');settle()
check('latest_search_after_loading_50000',len(t.tree.get_children())==500)
check('navigation_during_50000_load',app.current=='Serato')
app.show_page('TagStudio');settle();t.search.set('');settle();t.tree.selection_set(paths[:3]);settle()
for q in ('inexistant','artiste 1','réunion',''):t.search.set(q)
settle();check('rapid_search_latest_result',len(t.tree.get_children())==50000)
check('selection_preserved_after_coalesced_search',set(t.tree.selection())==set(paths[:3]))
t.sort_by('title');settle();check('sorting_and_selection',set(t.tree.selection())==set(paths[:3]) and t.tree.item(t.tree.get_children()[0],'values')[1]=='Titre 0')
seen=[];ui=threading.get_ident()
def producer():
 for i in range(1000):app.hub.post(lambda i=i:seen.append((i,threading.get_ident())))
 assert app.hub.ui(lambda:len(seen))==1000
app.hub.run('Test','File synthétique',producer);settle()
check('queue_fifo_and_only_ui_widget_execution',seen==[(i,ui) for i in range(1000)])
check('bounded_queue_and_single_worker',app.hub.messages.maxsize==384 and app.hub.worker.is_alive())
check('no_callback_or_worker_error',not errors)
check('clean_shutdown_worker_joined',app.hub.shutdown() and not app.hub.worker.is_alive());app.destroy()
print(json.dumps({'passed':len(checks),'checks':checks,'errors':errors,'platform':sys.platform},ensure_ascii=False,indent=2))
