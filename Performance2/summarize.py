"""Aggregate balanced P1/P2 runs without mixing platforms or preliminary data."""
import sys,json,statistics
from pathlib import Path
folder=Path(sys.argv[1]);runs={}
for label in ('P1_A','P2_A','P2_B','P1_B'):
 p=folder/(label+'.json')
 if not p.exists():raise SystemExit('Résultat manquant : '+str(p))
 runs[label]=json.loads(p.read_text(encoding='utf-8'))
 if runs[label].get('errors') or not runs[label].get('clean_shutdown'):raise SystemExit('Échec : '+label)
assert len({d['platform'] for d in runs.values()})==1,'Plateformes différentes'
def stats(v):
 s=sorted(v)
 def q(f):
  i=(len(s)-1)*f;k=int(i);return s[k]+(s[min(k+1,len(s)-1)]-s[k])*(i-k)
 return dict(n=len(v),median=statistics.median(v),min=min(v),max=max(v),p95=q(.95),p99=q(.99),iqr=q(.75)-q(.25))
def grouped(prefix,field):return [runs[prefix+'_'+s][field] for s in ('A','B')]
summary={'platform':runs['P1_A']['platform'],'python':runs['P1_A']['python'],'startup_ms':{},'rss_final_mib':{},'heartbeat_lag_ms':{},'measurements':{}}
for prefix in ('P1','P2'):
 summary['startup_ms'][prefix]=stats(grouped(prefix,'startup_ms'))
 summary['rss_final_mib'][prefix]=stats(grouped(prefix,'rss_final_mib'))
 summary['heartbeat_lag_ms'][prefix]=stats([v for d in grouped(prefix,'heartbeat_lag_ms') for v in d['samples']])
for name in runs['P1_A']['measurements']:
 summary['measurements'][name]={}
 for prefix in ('P1','P2'):
  items=[runs[prefix+'_'+s]['measurements'][name] for s in ('A','B')]
  summary['measurements'][name][prefix]={field:stats([v for d in items for v in d[field]['samples']]) for field in ('wall_ms','cpu_ms')}
  summary['measurements'][name][prefix]['rss_mib']=statistics.median(d['rss_mib'] for d in items)
(folder/'comparaison.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# Comparaison P1 / PERFORMANCE 2.1','',summary['platform'],'','Temps en millisecondes. Pooled médianes, IQR et maxima ; ordre P1/P2.1/P2.1/P1.','', '| Opération | P1 médiane | P2.1 médiane | Gain | IQR P1 / P2.1 | Max P1 / P2.1 |', '|---|---:|---:|---:|---:|---:|']
for name,d in summary['measurements'].items():
 b=d['P1']['wall_ms'];a=d['P2']['wall_ms'];gain=100*(b['median']-a['median'])/b['median']
 lines.append(f"| {name} | {b['median']:.2f} | {a['median']:.2f} | {gain:.1f} % | {b['iqr']:.2f} / {a['iqr']:.2f} | {b['max']:.2f} / {a['max']:.2f} |")
lines+=['','CPU (temps processus, ms) et RSS par scénario : voir comparaison.json.','', '| Mesure globale | P1 | P2.1 |','|---|---:|---:|']
for k in ('startup_ms','rss_final_mib'):
 lines.append(f"| {k} (médiane) | {summary[k]['P1']['median']:.2f} | {summary[k]['P2']['median']:.2f} |")
for stat in ('median','p95','p99','max'):lines.append(f"| Retard heartbeat {stat} ms | {summary['heartbeat_lag_ms']['P1'][stat]:.2f} | {summary['heartbeat_lag_ms']['P2'][stat]:.2f} |")
(folder/'COMPARAISON.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');print('\n'.join(lines))
