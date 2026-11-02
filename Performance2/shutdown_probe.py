"""Benchmark-only shutdown: check idle and stop in one UI callback, bounded wait."""
import time

def snapshot(app):
 hub=app.hub;tag=app.apps.get('TagStudio')
 return {'busy':hub.busy,'owner':hub.owner,'title':hub.title,'messages':hub.messages.qsize(),
         'deferred':len(hub.deferred),'populate_job':bool(tag and tag._populate_job),
         'dashboard_job':bool(app.dashboard._job),'worker_alive':hub.worker.is_alive(),
         'pending_timers':len(app.tk.call('after','info'))}

def clean_shutdown(app,timeout=30):
 started=time.perf_counter();result={'initial':snapshot(app),'attempts':0,'clean_shutdown':False}
 def poll():
  state=snapshot(app);result['last']=state
  if time.perf_counter()-started>=timeout:
   result['error']='Shutdown timeout; outstanding work was not discarded';app.quit();return
  if state['busy'] or state['messages'] or state['deferred'] or state['populate_job'] or state['dashboard_job']:
   app.after(1,poll);return
  # No update()/mainloop re-entry between the idle test and shutdown.
  result['attempts']+=1
  accepted=app.hub.shutdown()
  result['clean_shutdown']=bool(accepted and not app.hub.worker.is_alive() and app.hub.messages.empty() and not app.hub.deferred)
  result['final']=snapshot(app)
  if not result['clean_shutdown']:result['error']='Shutdown rejected or worker/messages still active'
  app.quit()
 app.after(0,poll);app.mainloop();result['duration_ms']=(time.perf_counter()-started)*1000
 return result
