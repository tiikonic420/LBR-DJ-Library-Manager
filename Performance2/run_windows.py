"""Reproducible P1/P2 campaign using the bundled Python; errors always nonzero."""
import sys,subprocess,json,datetime,argparse,os
from pathlib import Path
root=Path(__file__).resolve().parents[1]
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8',errors='replace')
p=argparse.ArgumentParser();p.add_argument('--sizes',default='1000,5000,10000,25000,50000');p.add_argument('--repeat',type=int,default=3);p.add_argument('--output',help='Dossier de preuves explicite (nouveau dossier uniquement)');args=p.parse_args()
sizes=[int(n) for n in args.sizes.split(',')]
if not sizes or any(n<1 or n>50000 for n in sizes) or not 1<=args.repeat<=20:raise SystemExit('Tailles : 1 à 50000 ; répétitions : 1 à 20.')
out=Path(args.output).resolve() if args.output else root/'RESULTATS_WINDOWS_P22'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f');out.mkdir(parents=True)
jobs=[('regression_11',[str(root/'Performance/test_regression.py')]),('gui_14',[str(root/'Performance/test_gui.py')]),('invariants_P2',[str(root/'Performance2/test_p2.py')]),('gui_P2',[str(root/'Performance2/test_gui_p2.py')]),('pixels_geometrie',[str(root/'Performance2/compare_render.py'),'--output',str(out/'captures')])]
for name,source in [('P1_A',root/'Reference_PERFORMANCE_1'),('P2_A',root/'_internal/app'),('P2_B',root/'_internal/app'),('P1_B',root/'Reference_PERFORMANCE_1')]:
 jobs.append((name,[str(root/'Performance2/benchmark.py'),'--source',str(source),'--output',str(out/(name+'.json')),'--sizes',args.sizes,'--repeat',str(args.repeat)]))
for name,source in [('P1_A',root/'Reference_PERFORMANCE_1'),('P2_A',root/'_internal/app'),('P2_B',root/'_internal/app'),('P1_B',root/'Reference_PERFORMANCE_1')]:
 jobs.append(('scroll_'+name,[str(root/'Performance2/scroll_probe.py'),str(source),str(out/('scroll_'+name+'.json'))]))
jobs.append(('comparaison',[str(root/'Performance2/summarize.py'),str(out)]))
jobs[5:5]=[('shutdown_P1',[str(root/'Performance2/test_shutdown.py'),str(root/'Reference_PERFORMANCE_1')]),('shutdown_P21',[str(root/'Performance2/test_shutdown.py'),str(root/'_internal/app')])]
status={}
for i,(name,argv) in enumerate(jobs,1):
 print(f'[{i}/{len(jobs)}] {name} — en cours',flush=True)
 try:
  with (out/(name+'.log')).open('w',encoding='utf-8') as log:
   r=subprocess.run([sys.executable,'-I','-X','utf8',*argv],cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=900)
  status[name]={'exit_code':r.returncode}
  report=out/(name+'.json')
  if report.exists():
   data=json.loads(report.read_text(encoding='utf-8'))
   if data.get('errors'):status[name]['errors']=data['errors']
 except subprocess.TimeoutExpired:status[name]={'error':'timeout après 900 secondes'}
 except OSError as e:status[name]={'error':str(e)}
 ok=status[name].get('exit_code')==0 and not status[name].get('errors')
 print(f'[{i}/{len(jobs)}] {name} — '+('OK' if ok else 'ÉCHEC (voir journal)'),flush=True)
 (out/'statut.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
print('Rapports : '+str(out),flush=True)
raise SystemExit(0 if all(v.get('exit_code')==0 and not v.get('errors') for v in status.values()) else 1)
