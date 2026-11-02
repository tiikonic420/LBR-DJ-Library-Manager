"""Read-only synthetic benchmarks. GUI mode requires a desktop/Tk display."""
import argparse, json, os, sys, tempfile, time, statistics, platform, cProfile
from pathlib import Path
P=argparse.ArgumentParser();P.add_argument('--source',required=True);P.add_argument('--output',required=True);P.add_argument('--gui',action='store_true');P.add_argument('--rows',type=int,default=5000);A=P.parse_args()
source=Path(A.source).resolve();output=Path(A.output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
isolated=tempfile.TemporaryDirectory(prefix='lbr_perf_');home=Path(isolated.name)
for key in ('APPDATA','LOCALAPPDATA','USERPROFILE','HOME'):os.environ[key]=str(home)
# No professional files, external process, or audio writes in these scenarios.
sys.path[:0]=[str(source),str(source/'modules')]
import psutil
try:process=psutil.Process()
except psutil.Error:process=None
def rss():
 try:
  if process:return process.memory_info().rss/1048576
  for line in Path('/proc/self/status').read_text().splitlines():
   if line.startswith('VmRSS:'):return int(line.split()[1])/1024
 except (psutil.Error,OSError):pass
 return None
results={'system':platform.platform(),'python':sys.version,'rows':A.rows,'gui':A.gui,'measurements':{}}
def measure(name,fn,n=7):
 samples=[];cpu=[]
 for _ in range(n):
  c=time.process_time();t=time.perf_counter();fn();samples.append((time.perf_counter()-t)*1000);cpu.append((time.process_time()-c)*1000)
 results['measurements'][name]={'median_ms':statistics.median(samples),'max_ms':max(samples),'samples_ms':samples,'cpu_median_ms':statistics.median(cpu),'cpu_percent_one_core':100*sum(cpu)/sum(samples)}
 print(name,round(statistics.median(samples),3),flush=True)
 return samples
class Var:
 def __init__(self,v=''):self.v=v
 def get(self):return self.v
 def set(self,v):self.v=v
class Tree:
 def __init__(self):self.data={};self.order=[];self.sel=();self.calls=0
 def selection(self):return self.sel
 def selection_set(self,v):self.sel=tuple(v)
 def insert(self,parent,index,iid=None,**kw):
  iid=iid or str(len(self.data));self.data[iid]=kw;self.order.append(iid);self.calls+=1;return iid
 def item(self,iid,option=None,**kw):
  self.calls+=1
  if kw:self.data.setdefault(iid,{}).update(kw)
  return self.data.get(iid,{}).get(option,()) if option else self.data.get(iid,{})
 def delete(self,*ids):
  for i in ids:self.data.pop(i,None)
  gone=set(ids);self.order=[i for i in self.order if i not in gone]
 def set_children(self,parent,*ids):self.order=list(ids)
 def tag_configure(self,*a,**kw):pass
 def get_children(self,*a):return tuple(self.order)
class Hub:
 def on_ui(self):return False
 def post(self,fn,*a,**kw):return fn(*a,**kw)
def rows():
 return {str(home/'music'/f'genre{i%20}'/f'{i}.flac'):{'file':f'{i}.flac','path':str(home/'music'/f'genre{i%20}'/f'{i}.flac'),'title':f'Titre {i}','artist':f'Artiste {i%100}','album':'Été Réunion','genre':'Maloya','date':'2026','comment':'démo','bpm':'120'} for i in range(A.rows)}
if not A.gui:
 import tag_studio as tag,rekordbox_serato_v1_4 as serato
 from types import SimpleNamespace
 a=object.__new__(tag.App);a.host=SimpleNamespace(hub=Hub(),colors={'green':'green'});a.rows=rows();a.pending={};a.cols=['file','title','artist','album','genre','date','track','bpm','key','serato','rekordbox'];a.tree=Tree();a.search=Var();a.status=Var();a.folder=str(home/'music');a.active_filter='';a._rendered_rows={};a._visible_order=()
 measure('tag_initial_model_fake_widgets',lambda:(setattr(a,'_rendered_rows',{}),setattr(a,'_visible_order',()),setattr(a,'tree',Tree()),a.populate()),3)
 def search():
  for q in ('artiste 12','réunion','absent',''):
   a.search.set(q)
   if 'reuse' in tag.App.populate.__code__.co_varnames:a.populate(reuse=True)
   else:a.populate()
 measure('tag_four_searches_fake_widgets',search)
 profiler=cProfile.Profile();profiler.runcall(search);profiler.dump_stats(str(output.with_suffix('.prof')))
 b=object.__new__(serato.App);b.serato_path=Var(str(home/'_Serato_'));b.playlists=[serato.Node(f'Playlist {i}','playlist',tracks=[str(home/f'{j}.wav') for j in range(40)]) for i in range(100)];b.item_to_node={str(i):pl for i,pl in enumerate(b.playlists)};b.tree=Tree();b.summary=Var();b.serato_state=Var();b.write_log=lambda *a,**kw:None
 measure('serato_compare_100_playlists_missing_synthetic',b.refresh_statuses)
 results['rss_mib']=rss()
else:
 import tkinter as tk
 import rekordsync_v5_0_6 as rb,rekordbox_serato_v1_4 as sr
 rb.rbsync_python=lambda:None;sr.find_serato_roots=lambda:[]
 errors=[];start=time.perf_counter()
 from LBR_DJ_Library_Manager_FINAL import LBRManager
 app=LBRManager();app.report_callback_exception=lambda *e:errors.append(str(e));app.report_task_error=lambda *e:errors.append(str(e))
 beats=[];last=[time.perf_counter()]
 def beat():
  now=time.perf_counter();beats.append(max(0,(now-last[0])*1000-10));last[0]=now;app.after(10,beat)
 app.after(10,beat)
 def wait_idle():
  deadline=time.perf_counter()+120
  def poll():
   if time.perf_counter()>deadline:errors.append('TIMEOUT');app.quit();return
   tag=app.apps.get('TagStudio')
   if app.hub.busy or app.hub.deferred or not app.hub.messages.empty() or (tag and tag._populate_job) or app.dashboard._job:app.after(1,poll)
   else:app.after_idle(app.quit)
  app.after(0,poll);app.mainloop();app.update_idletasks()
 wait_idle();results['measurements']['startup']={'median_ms':(time.perf_counter()-start)*1000}
 for page in app.nav:
  measure('first_page_'+page,lambda p=page:(app.show_page(p),wait_idle()),1)
 # Settle startup timers without touching a real installation.
 app.after(1200,app.quit);app.mainloop();wait_idle()
 for page in app.nav:
  def transition(p=page):
   app.show_page('Accueil' if p!='Accueil' else 'Paramètres');wait_idle()
   t=time.perf_counter();app.show_page(p);wait_idle();return (time.perf_counter()-t)*1000
  samples=[transition() for _ in range(5)]
  results['measurements']['navigation_'+page]={'median_ms':statistics.median(samples),'samples_ms':samples}
 def nav():
  for page in app.nav:app.show_page(page);wait_idle()
 measure('seven_page_roundtrip',nav)
 for page in app.nav:
  app.show_page(page);wait_idle()
  measure('theme_'+page,lambda:(app.set_theme('clair' if app.mode=='sombre' else 'sombre'),wait_idle()),6)
 app.show_page('TagStudio');wait_idle();a=app.apps['TagStudio'];a.folder=str(home/'music');a.rows=rows()
 measure('tag_initial_table',lambda:(a.populate(),wait_idle()),1)
 # Measure complete debounce + worker + table updates, not just dispatch.
 for q in ('artiste 12','réunion','absent',''):
  def query(q=q):
   a.search.set(q);wait_idle()
  measure('search_'+(q or 'empty'),query,3)
 measure('scroll_100_steps',lambda:[(a.tree.yview_scroll(1,'units'),app.update_idletasks()) for _ in range(100)],3)
 results['rss_mib']=rss()
 results['heartbeat_lag_ms']={'max':max(beats,default=0),'p95':sorted(beats)[int(.95*(len(beats)-1))] if beats else 0,'samples':len(beats)}
 results['errors']=errors
 assert app.hub.shutdown();app.destroy()
output.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(results,ensure_ascii=False,indent=2))
