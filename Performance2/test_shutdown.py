"""Deterministic reproduction of late work, timeout and real TaskHub clean join."""
import sys,os,tempfile,time,json,threading
from pathlib import Path
src=Path(sys.argv[1]).resolve();tmp=tempfile.TemporaryDirectory(prefix='lbr_shutdown_')
for k in ('HOME','USERPROFILE','APPDATA','LOCALAPPDATA'):os.environ[k]=tmp.name
sys.path[:0]=[str(src),str(src/'modules'),str(Path(__file__).resolve().parent)]
import rekordsync_v5_0_6 as rb,rekordbox_serato_v1_4 as se
rb.rbsync_python=lambda:None;se.find_serato_roots=lambda:[]
from LBR_DJ_Library_Manager_FINAL import LBRManager
from shutdown_probe import clean_shutdown
app=LBRManager();errors=[];seen=[];ui=threading.get_ident()
app.report_task_error=lambda *e:errors.append(str(e));app.report_callback_exception=lambda *e:errors.append(str(e))
gate=threading.Event()
def work():
 assert gate.wait(15), "Test gate timeout"
 for i in range(50):app.hub.post(lambda i=i:seen.append((i,threading.get_ident())))
assert not app.hub.busy
# Work becomes ready after the idle check, exactly the gap in the old protocol.
app.after(0,lambda:app.hub.run('Test','Late periodic work',work));app.update()
assert app.hub.busy
old_result=app.hub.shutdown();assert old_result is False
short=clean_shutdown(app,timeout=.005);assert not short['clean_shutdown'] and 'timeout' in short['error'].lower()
assert not app.hub.stopped # No forced cancellation, no fabricated PASS.
gate.set()
final=clean_shutdown(app,timeout=10)
assert final['clean_shutdown'];assert not app.hub.worker.is_alive()
assert seen==[(i,ui) for i in range(50)];assert not errors
app.destroy()
print(json.dumps({'old_protocol_reproduced':not old_result,'timeout_correctly_failed':True,'all_50_updates_drained_on_ui':True,'clean_shutdown':True,'worker_joined':True,'diagnostic':final,'errors':errors},indent=2))
