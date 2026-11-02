import ast,json,types,tempfile,hashlib
from pathlib import Path
from unittest.mock import Mock
root=Path.cwd(); base=root/'release40rc2';lib=base/'payload/_internal/python/Lib';results={}
old=root/'release40/payload/_internal/python/Lib/importlib/metadata/__init__.py'
try:ast.parse(old.read_bytes());raise AssertionError('Old failure absent')
except IndentationError as e:assert e.lineno==648;results['rc1_failure_reproduced']=str(e)
files=list(lib.rglob('*.py'))
for p in files:ast.parse(p.read_bytes(),filename=str(p))
results['runtime_python_files_parsed']=len(files)
compared=0
for p in (base/'official/Lib').rglob('*'):
 q=lib/p.relative_to(base/'official/Lib')
 if p.is_file() and q.is_file():assert p.read_bytes()==q.read_bytes(),str(q);compared+=1
results['official_msi_files_equal']=compared
src=base/'payload/_internal/app/modules/rekordsync_v5_0_6.py';tree=ast.parse(src.read_bytes());cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='App');methods=[x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name in ('refresh_rb_folders','sync_one_click','install')]
class Widget(dict):
 def configure(self,**kw):self.update(kw)
class Var:
 def __init__(self,v=''):self.v=v
 def set(self,v):self.v=v
 def get(self):return self.v
with tempfile.TemporaryDirectory() as tmp:
 g={'rbsync_python':lambda:'python.exe','CFG_DIR':Path(tmp),'run_process':Mock(),'APP':'test','messagebox':Mock(),'find_rbsync':lambda:True}
 exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.ClassDef(name='TestApp',bases=[],keywords=[],body=methods,decorator_list=[])],type_ignores=[])),'test','exec'),g)
 a=g['TestApp']();a.rb_combo=Widget();a.rb_folder=Var('MUSIC 2026');a.sync_btn=Widget();a.status=Var();a.append=Mock();a.source_path=lambda:Path('MUSIC 2026');a.update_sync_button=Mock();a.doctor=Mock()
 g['run_process'].return_value=types.SimpleNamespace(returncode=1,stderr='IndentationError line 648',stdout='')
 a.refresh_rb_folders();assert a._rb_read_failed and not a.rb_combo['values'] and not a.rb_targets and a.sync_btn['state']=='disabled';assert 'IndentationError' in a.append.call_args.args[0]
 a.sync_one_click();g['messagebox'].showerror.assert_called_once()
 g['run_process'].return_value=types.SimpleNamespace(returncode=0,stderr='',stdout='FOLDER=MUSIC 2026\nPLAYLIST=MUSIC 2026 / AFRO 2026\n')
 a.refresh_rb_folders();assert not a._rb_read_failed and a.sync_btn['state']=='normal';assert ('playlist','MUSIC 2026 / AFRO 2026') in a.rb_targets.values()
 a.install();a.doctor.assert_called_once()
 g['rbsync_python']=lambda:None;a.refresh_rb_folders();assert a._rb_read_failed and not a.rb_combo['values'] and a.sync_btn['state']=='disabled'
results['rekordsync_error_success_missing_runtime_and_diagnostic']='PASS'
for p in (base/'payload/_internal/app').rglob('*.py'):ast.parse(p.read_bytes())
results['windows_execution']='Not performed: must validate on Windows PC'
(base/'test_results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
