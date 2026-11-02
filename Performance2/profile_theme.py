import sys,os,tempfile,time,cProfile,pstats,json
from pathlib import Path
sys.dont_write_bytecode=True
src=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
tmp=tempfile.TemporaryDirectory(prefix='lbr_theme_')
for key in ('HOME','USERPROFILE','APPDATA','LOCALAPPDATA'):os.environ[key]=tmp.name
sys.path[:0]=[str(src),str(src/'modules')]
import rekordsync_v5_0_6 as rb,rekordbox_serato_v1_4 as se
rb.rbsync_python=lambda:None;se.find_serato_roots=lambda:[]
from LBR_DJ_Library_Manager_FINAL import LBRManager
app=LBRManager();errors=[];app.report_callback_exception=lambda *e:errors.append(str(e));app.report_task_error=lambda *e:errors.append(str(e))
def settle():
 def poll():
  if app.hub.busy or app.hub.deferred or app.dashboard._job:app.after(1,poll)
  else:app.after_idle(app.quit)
 app.after(0,poll);app.mainloop();app.update_idletasks()
for k in app.nav:app.show_page(k);settle()
app.after(1200,app.quit);app.mainloop();settle()
results={}
for page in ['TagStudio','Serato','Paramètres']:
 app.show_page(page);settle();stats=[];prof=cProfile.Profile();prof.enable()
 for i in range(6):
  t=time.perf_counter();app.set_theme('clair' if app.mode=='sombre' else 'sombre');callback=(time.perf_counter()-t)*1000
  settle();stats.append({'callback_ms':callback,'settled_ms':(time.perf_counter()-t)*1000})
 prof.disable();prof.dump_stats(str(out/(page+'.prof')))
 with (out/(page+'.txt')).open('w',encoding='utf-8') as f:pstats.Stats(prof,stream=f).sort_stats('cumulative').print_stats(40)
 results[page]=stats
print(json.dumps(results,indent=2));print('errors',errors)
app.hub.shutdown();app.destroy()
