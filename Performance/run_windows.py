"""Run all measurements with the bundled interpreter, in isolated child processes."""
import sys,subprocess,json,datetime,argparse
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--rows',type=int,default=5000);args=p.parse_args()
if not 1<=args.rows<=100000:raise SystemExit('Nombre de lignes attendu : 1 a 100000')
out=root/'RESULTATS_WINDOWS'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True)
jobs=[('regression',[str(root/'Performance/test_regression.py')]),('gui_tests',[str(root/'Performance/test_gui.py')])]
for label,source in [('avant',root/'Reference_RC2'),('apres',root/'_internal/app')]:
 for gui in (False,True):
  name=label+('_gui' if gui else '_modele')
  jobs.append((name,[str(root/'Performance/bench.py'),'--source',str(source),'--output',str(out/(name+'.json')),'--rows',str(args.rows)]+(['--gui'] if gui else [])))
status={}
for i,(name,argv) in enumerate(jobs,1):
 print(f'[{i}/{len(jobs)}] {name}',flush=True)
 try:
  with (out/(name+'.log')).open('w',encoding='utf-8') as log:
   r=subprocess.run([sys.executable,'-I',*argv],cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=300)
  status[name]={'exit_code':r.returncode}
  report=out/(name+'.json')
  if report.exists():
   data=json.loads(report.read_text(encoding='utf-8'))
   if data.get('errors'):status[name]['errors']=data['errors']
 except subprocess.TimeoutExpired:status[name]={'error':'timeout after 300 seconds'}
(out/'statut.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
print('Rapports : '+str(out))
raise SystemExit(0 if all(v.get('exit_code')==0 and not v.get('errors') for v in status.values()) else 1)
