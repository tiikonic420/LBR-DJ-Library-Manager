"""Identical P1/P2 synthetic GUI scenarios; never opens a professional library."""
import argparse,json,os,sys,tempfile,time,statistics,platform
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True);p.add_argument('--sizes',default='1000,5000,10000,25000,50000');p.add_argument('--repeat',type=int,default=3);a=p.parse_args()
sys.dont_write_bytecode=True
source=Path(a.source).resolve();output=Path(a.output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
tmp=tempfile.TemporaryDirectory(prefix='LBR_synthetique_');home=Path(tmp.name)
for k in ('HOME','USERPROFILE','APPDATA','LOCALAPPDATA'):os.environ[k]=str(home)
sys.path[:0]=[str(source),str(source/'modules')]
import rekordsync_v5_0_6 as rb,rekordbox_serato_v1_4 as se,tag_studio as tag
rb.rbsync_python=lambda:None;se.find_serato_roots=lambda:[];tag.read_cover=lambda _:None
try:
 import psutil
 process=psutil.Process()
except Exception:process=None
def rss():
 if process:return process.memory_info().rss/1048576
 try:
  return int(next(x for x in Path('/proc/self/status').read_text(encoding='utf-8').splitlines() if x.startswith('VmRSS:')).split()[1])/1024
 except (OSError,StopIteration):return None
def stats(xs):
 s=sorted(xs)
 def q(p):
  i=(len(s)-1)*p;l=int(i);return s[l]+(s[min(l+1,len(s)-1)]-s[l])*(i-l)
 return {'n':len(s),'median':statistics.median(s),'p95':q(.95),'p99':q(.99),'max':max(s),'min':min(s),'iqr':q(.75)-q(.25),'samples':xs}
result={'platform':platform.platform(),'python':sys.version,'measurements':{},'errors':[]};errors=result['errors'];beats=[];deadline=[time.perf_counter()+.010]
start=time.perf_counter()
from LBR_DJ_Library_Manager_FINAL import LBRManager
app=LBRManager();result['tk_version']=app.tk.call('package','present','Tk');app.report_callback_exception=lambda *e:errors.append(str(e));app.report_task_error=lambda *e:errors.append(str(e))
def beat():
 now=time.perf_counter();beats.append(max(0,(now-deadline[0])*1000));deadline[0]=now+.010;app.after(10,beat)
app.after(10,beat)
def settle():
 end=time.perf_counter()+180
 def poll():
  if time.perf_counter()>end:errors.append('timeout');app.quit();return
  t=app.apps.get('TagStudio')
  if app.hub.busy or app.hub.deferred or not app.hub.messages.empty() or (t and t._populate_job) or app.dashboard._job:app.after(1,poll)
  else:app.after_idle(app.quit)
 app.after(0,poll);app.mainloop();app.update_idletasks();app.update()
def record(name,fn,n=None):
 samples=[];cpu=[];lags=[]
 for _ in range(n or a.repeat):
  first=len(beats);c=time.process_time();t=time.perf_counter();fn();settle();samples.append((time.perf_counter()-t)*1000);cpu.append((time.process_time()-c)*1000);lags.extend(beats[first:])
 result['measurements'][name]={'wall_ms':stats(samples),'cpu_ms':stats(cpu),'rss_mib':rss(),'lag_ms':stats(lags) if lags else None}
 print(name,round(statistics.median(samples),2),flush=True)
 output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
settle();result['startup_ms']=(time.perf_counter()-start)*1000
for page in app.nav:
 record('startup_followup_idle' if page=='Accueil' else 'first/'+page,lambda page=page:app.show_page(page),1)
app.after(1200,app.quit);app.mainloop();settle()
for page in app.nav:
 samples=[]
 def nav(page=page):
  app.show_page('Accueil' if page!='Accueil' else 'Paramètres');settle();app.show_page(page)
 record('navigation_pair/'+page,nav)
for page in app.nav:
 app.show_page(page);settle();record('theme/'+page,lambda:app.set_theme('clair' if app.mode=='sombre' else 'sombre'),6)
app.show_page('TagStudio');settle();t=app.apps['TagStudio'];t.folder=str(home/'music')
for count in map(int,a.sizes.split(',')):
 def load():
  t.search.set('');settle()
  existing=t.tree.get_children()
  if existing:t.tree.delete(*existing)
  t._rendered_rows={};t._visible_order=()
  t.rows={str(home/'music'/f'genre{i%20}'/f'{i}.flac'):{'path':str(home/'music'/f'genre{i%20}'/f'{i}.flac'),'file':f'{i}.flac','title':f'Titre {i}','artist':f'Artiste {i%100}','album':'Été Réunion','genre':'Maloya','date':'2026','bpm':'120'} for i in range(count)}
  t.populate()
 record(f'load/{count}',load)
 assert len(t.tree.get_children())==count
 def search():
  for q in ('artiste 12','réunion','absent',''):t.search.set(q);settle()
 record(f'four_searches/{count}',search)
 def filtered():
  for folder in ('genre2',''):t.active_filter=folder;t.populate(reuse=True);settle()
 record(f'folder_filter/{count}',filtered)
 def scroll():
  t.tree.yview_moveto(0)
  remaining=[100]
  def step():
   t.tree.yview_scroll(1,'units');remaining[0]-=1
   if remaining[0]:app.after(1,step)
   else:app.after_idle(app.quit)
  app.after(0,step);app.mainloop()
 record(f'scroll_100/{count}',scroll)
 record(f'theme_loaded/{count}',lambda:app.set_theme('clair' if app.mode=='sombre' else 'sombre'),6)
 def busy_nav():
  t.populate();app.show_page('MusicGenre');app.set_theme('clair' if app.mode=='sombre' else 'sombre');settle();app.show_page('TagStudio')
 record(f'navigate_during_load/{count}',busy_nav)
 assert len(t.tree.get_children())==count
result['heartbeat_lag_ms']=stats(beats);result['rss_final_mib']=rss()
# Lifecycle wait is outside the recorded performance samples.
sys.path.insert(0,str(Path(__file__).resolve().parent))
from shutdown_probe import clean_shutdown
result['shutdown_diagnostic']=clean_shutdown(app)
result['clean_shutdown']=result['shutdown_diagnostic']['clean_shutdown']
if result['clean_shutdown']:app.destroy()
output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
assert not errors,errors
assert result['clean_shutdown']
