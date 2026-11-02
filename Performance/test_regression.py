"""Differential tests on synthetic data only; no audio/database writes."""
import unittest,ast,types,sys,tempfile,os,random,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'Reference_RC2';NEW=ROOT/'Sources_application'
if not BASE.exists():BASE=ROOT.parent/'baseline/LBR_DJ_Library_Manager_4.0_RC2/Sources_application'
sys.path[:0]=[str(NEW),str(NEW/'modules')]
import tkinter as tk
from tkinter import ttk
from unittest.mock import Mock

def extract(path,name,methods):
 tree=ast.parse(path.read_text(encoding='utf-8'));cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==name)
 body=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in methods]
 scope={'Path':Path,'os':os,'tk':tk,'ttk':ttk}
 node=ast.ClassDef(name='Controller',bases=[],keywords=[],body=body,decorator_list=[])
 exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(path),'exec'),scope)
 return scope['Controller']
class Var:
 def __init__(self,v=''):self.v=v
 def get(self):return self.v
 def set(self,v):self.v=v
class Tree:
 def __init__(self):self.data={};self.order=[];self.sel=();self.writes=0;self.select_calls=0
 def selection(self):return self.sel
 def selection_set(self,v):self.sel=tuple(v);self.select_calls+=1
 def insert(self,parent,index,iid=None,**kw):
  iid=iid or str(len(self.data));self.data[iid]=kw;self.order.append(iid);self.writes+=1;return iid
 def item(self,iid,option=None,**kw):
  if kw:self.data[iid].update(kw);self.writes+=1
  return self.data.get(iid,{}).get(option,()) if option else self.data.get(iid,{})
 def delete(self,*ids):
  for i in ids:self.data.pop(i,None)
  ids=set(ids);self.order=[i for i in self.order if i not in ids];self.sel=tuple(i for i in self.sel if i not in ids)
 def set_children(self,parent,*ids):self.order=list(ids)
 def tag_configure(self,*a,**kw):pass
 def get_children(self,*a):return tuple(self.order)
class Hub:
 def on_ui(self):return False
 def post(self,fn,*a,**kw):return fn(*a,**kw)
def tag_app(root):
 C=extract(root/'modules/tag_studio.py','App',{'populate','_apply_row_changes','sort_by'})
 a=C();a.host=types.SimpleNamespace(hub=Hub(),colors={'green':'green'})
 a.rows={f'/synthetic/genre{i%5}/{i}.flac':{'title':f'Titre {i}','artist':'LÉA CHURROS' if i%2 else 'Maloya','comment':'Straße','path':f'/synthetic/genre{i%5}/{i}.flac','date':'2026'} for i in range(1000)}
 a.pending={};a.cols=['title','artist','date'];a.folder='/synthetic';a.active_filter='';a.tree=Tree();a.search=Var();a.status=Var();a._rendered_rows={};a._visible_order=();return a
class Regression(unittest.TestCase):
 def setUp(self):self.before=tag_app(BASE);self.after=tag_app(NEW)
 def same(self):
  a,b=self.before,self.after
  self.assertEqual(a.tree.data,b.tree.data);self.assertEqual(a.tree.order,b.tree.order);self.assertEqual(set(a.tree.sel),set(b.tree.sel));self.assertEqual(a.status.get(),b.status.get())
 def populate(self,reuse=False):
  self.before.populate();self.after.populate(reuse=reuse);self.same()
 def test_initial_1000(self):self.populate()
 def test_search_unicode_all_fields_folder(self):
  self.populate()
  for folder in ('','Tous les dossiers','genre1','genre4'):
   for q in ('léa','STRASSE','2026','synthetic','absent',''):
    for a in (self.before,self.after):a.active_filter=folder;a.search.set(q.casefold())
    self.populate(True)
 def test_pending_edit_clear_and_read_refresh(self):
  self.populate();p=next(iter(self.after.rows))
  for a in (self.before,self.after):a.pending[p]={'title':'NOUVEAU'};a.search.set('nouveau')
  self.populate()
  for a in (self.before,self.after):a.pending.clear();a.rows[p]['title']='RELU'
  self.populate()
  for a in (self.before,self.after):a.search.set('relu')
  self.populate(True)
 def test_rename_add_delete(self):
  self.populate();p=next(iter(self.after.rows))
  for a in (self.before,self.after):
   a.rows['/synthetic/new/a.flac']=a.rows.pop(p);a.rows['/synthetic/new/b.flac']={'title':'ajout'}
  self.populate()
 def test_selection_and_sort(self):
  self.populate()
  for a in (self.before,self.after):a.tree.sel=tuple(list(a.rows)[:4]);a.sort_by('title')
  self.same();self.populate(True)
  for a in (self.before,self.after):a.search.set('Titre 1')
  self.populate(True)
 def test_no_redundant_row_writes_or_selection_events(self):
  a=self.after;a.populate();n=a.tree.writes;events=a.tree.select_calls
  for q in ('léa','absent',''):a.search.set(q);a.populate(reuse=True)
  self.assertEqual(n,a.tree.writes);self.assertEqual(events,a.tree.select_calls)
 def test_random_edits_and_searches(self):
  rng=random.Random(17);self.populate()
  for i in range(60):
   p=rng.choice(list(self.after.rows));query=rng.choice(['','léa','edit','absent','titre 1'])
   edit=i%3==0
   for a in (self.before,self.after):
    a.search.set(query)
    if edit:a.pending[p]={'title':'edit '+str(i)}
   self.populate(not edit)
 def test_serato_refresh_outputs_and_call_count(self):
  outputs=[];counts=[]
  for root in (BASE,NEW):
   C=extract(root/'modules/rekordbox_serato_v1_4.py','App',{'refresh_statuses'});a=C()
   a.playlists=[types.SimpleNamespace(node_type='playlist',tracks=['x']*i,display_path=str(i)) for i in range(20)]
   a.item_to_node={str(i):n for i,n in enumerate(a.playlists[:12])};a.tree=Tree();a.tree.data={i:{} for i in a.item_to_node};a.summary=Var();a.serato_state=Var();a.serato_path=Var('/nonexistent_test');a.write_log=Mock()
   a.compare_playlist=Mock(side_effect=lambda p:('IDENTIQUE',0,0) if len(p.tracks)%2 else ('À CRÉER',len(p.tracks),0));a.refresh_statuses()
   outputs.append((a.tree.data,a.summary.get(),a.serato_state.get(),a.write_log.call_args));counts.append(a.compare_playlist.call_count)
  self.assertEqual(*outputs);self.assertEqual(counts,[32,20])
 def test_business_functions_unchanged(self):
  # Compare every function AST except explicitly optimized presentation methods.
  allowed={'tag_studio.py':{'populate','_render_request','select_folder','schedule_search'},'musicgenre_v2.py':{'clear'},'rekordbox_serato_v1_4.py':{'refresh_statuses','apply_playlist_filter'}}
  for p in (BASE/'modules').glob('*.py'):
   # FINAL includes the verified RekordSync 2.3 fix absent from RC2.
   reference=ROOT/'Reference_FINAL/modules'/p.name if p.name=='rekordsync_v5_0_6.py' and (ROOT/'Reference_FINAL').exists() else p
   old=ast.parse(reference.read_text(encoding='utf-8'));new=ast.parse((NEW/'modules'/p.name).read_text(encoding='utf-8'))
   def signatures(t):return {n.name:ast.dump(n,include_attributes=False) for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name not in allowed.get(p.name,set()) and n.name!='matches'}
   # Parent functions contain nested matches; excluded explicitly above.
   self.assertEqual(signatures(old),signatures(new),p.name)
 def test_metadata_cache_invalidation_and_copy(self):
  from task_hub import MetadataCache
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'dummy.txt';p.write_text('a');reader=Mock(return_value={'value':['a']});c=MetadataCache()
   c.read('tags',reader,p)['value'].append('modified');self.assertEqual(c.read('tags',reader,p),{'value':['a']});self.assertEqual(reader.call_count,1)
   p.write_text('longer');c.read('tags',reader,p);self.assertEqual(reader.call_count,2)
   c.invalidate(p);c.read('tags',reader,p);self.assertEqual(reader.call_count,3)
 def test_syntax_all_sources(self):
  for p in NEW.rglob('*.py'):ast.parse(p.read_bytes(),filename=str(p))
  ast.parse((NEW/'start.pyw').read_bytes())
if __name__=='__main__':unittest.main(verbosity=2)
