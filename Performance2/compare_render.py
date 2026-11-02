"""Strict comparison; retain every capture, difference and metadata on failure."""
import sys,subprocess,json,argparse,datetime
from pathlib import Path
from PIL import Image,ImageChops
root=Path(__file__).resolve().parents[1];base=root/'Reference_PERFORMANCE_1'
p=argparse.ArgumentParser();p.add_argument('--output');a=p.parse_args()
folder=Path(a.output).resolve() if a.output else root/'RESULTATS_VISUELS'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
folder.mkdir(parents=True,exist_ok=True);result={'platform':sys.platform,'captures':{},'probes':{},'passed':0,'cases':400,'strict_pixel_equality':True}
for label,src in [('P1',base),('P21',root/'Sources_application')]:
 with (folder/(label+'.log')).open('w',encoding='utf-8') as log:
  try:r=subprocess.run([sys.executable,'-I','-X','utf8',str(root/'Performance2/render_probe.py'),str(src),str(folder/label)],stdout=log,stderr=subprocess.STDOUT,timeout=180);result['probes'][label]=r.returncode
  except subprocess.TimeoutExpired:result['probes'][label]='timeout'
for mode in ('clair','sombre'):
 for state in ('normal','active','disabled','focus'):
  for page in range(2):
   name=f'{mode}_{state}_{page}';p=folder/'P1'/(name+'.png');q=folder/'P21'/(name+'.png')
   if not p.exists() or not q.exists():result['captures'][name]={'error':'missing capture'};continue
   with Image.open(p) as x,Image.open(q) as y:
    x=x.convert('RGB');y=y.convert('RGB')
    if x.size!=y.size:result['captures'][name]={'error':'size mismatch','sizes':[x.size,y.size]};continue
    diff=ImageChops.difference(x,y);bbox=diff.getbbox();diff.save(folder/(name+'_diff.png'))
    pixels=sum(any(v) for v in diff.getdata());maximum=max(hi for lo,hi in diff.getextrema())
   geometry=p.with_suffix('.json').read_bytes()==q.with_suffix('.json').read_bytes()
   result['captures'][name]={'bbox':bbox,'different_pixels':pixels,'max_channel_delta':maximum,'geometry_equal':geometry}
   if bbox is None and geometry:result['passed']+=1
result['success']=result['passed']==16 and all(v==0 for v in result['probes'].values())
(folder/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2));print('Evidence: '+str(folder))
raise SystemExit(0 if result['success'] else 1)
