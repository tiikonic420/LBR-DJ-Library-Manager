"""Isolate scroll cost after settling all population callbacks; real event loop."""
import sys,os,tempfile,time,json,statistics
from pathlib import Path
src=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]);tmp=tempfile.TemporaryDirectory(prefix='lbr_scroll_')
for k in ('HOME','USERPROFILE','APPDATA','LOCALAPPDATA'):os.environ[k]=tmp.name
sys.path[:0]=[str(src),str(src/'modules')]
import rekordsync_v5_0_6 as rb,rekordbox_serato_v1_4 as se
rb.rbsync_python=lambda:None;se.find_serato_roots=lambda:[]
import tag_studio as tag
tag.read_cover=lambda _:None
from LBR_DJ_Library_Manager_FINAL import LBRManager
app=LBRManager();errors=[];app.report_callback_exception=lambda *e:errors.append(str(e));app.report_task_error=lambda *e:errors.append(str(e))
def settle():
 def poll():
  if app.hub.busy or not app.hub.messages.empty():app.after(1,poll)
  else:app.after(500,app.quit)
 app.after(0,poll);app.mainloop();app.update()
for page in app.nav:app.show_page(page);settle()
app.show_page('TagStudio');t=app.apps['TagStudio'];t.folder=tmp.name
t.rows={str(Path(tmp.name)/f'{i}.flac'):{'file':f'{i}.flac','title':f'Titre {i}'} for i in range(50000)};t.populate()
settle();values=[];cpu=[]
for rep in range(24):
 t.tree.yview_moveto(0);app.update();n=[0]
 def step():
  t.tree.yview_scroll(1,'units');n[0]+=1
  if n[0]<100:app.after(1,step)
  else:app.after_idle(app.quit)
 c=time.process_time();s=time.perf_counter();app.after(0,step);app.mainloop();app.update()
 if rep>=4:values.append((time.perf_counter()-s)*1000);cpu.append((time.process_time()-c)*1000)
result={'wall_ms':values,'median_ms':statistics.median(values),'cpu_median_ms':statistics.median(cpu),'errors':errors}
sys.path.insert(0,str(Path(__file__).resolve().parent))
from shutdown_probe import clean_shutdown
result['shutdown_diagnostic']=clean_shutdown(app);result['clean_shutdown']=result['shutdown_diagnostic']['clean_shutdown']
out.write_text(json.dumps(result,indent=2),encoding='utf-8');print(result['median_ms'],result['cpu_median_ms'])
assert not errors;assert result['clean_shutdown']
app.destroy()
