"""No desktop needed: exercise contamination recovery and evidence retention."""
import ast,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
from PIL import Image

class GuardRecovery(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  tree=ast.parse(Path(__file__).with_name('render_probe.py').read_text(encoding='utf-8'))
  node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='guarded_grab')
  self.grab=Mock(return_value=Image.new('RGB',(4,4),'red'))
  self.status=Mock();self.root=Mock();self.flush=Mock()
  self.scope={'desktop_status':self.status,'ImageGrab':Mock(grab=self.grab),
   'out':Path(self.tmp.name),'report':{'invalid_attempts':[],'capture_attempts':[]},'root':self.root,
   'time':Mock(),'flush':self.flush,'sys':Mock(platform='test'),'os':Mock(environ={})}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])), '<guard>', 'exec'),self.scope)
 def run_guard(self):return self.scope['guarded_grab']((0,0,4,4),'case',0)
 def test_valid_capture_is_accepted_once(self):
  self.status.return_value={'valid':True};im,meta=self.run_guard()
  self.assertEqual(self.grab.call_count,1);self.assertEqual(meta['attempt'],0)
  self.root.lift.assert_not_called()
 def test_occluded_before_capture_is_not_grabbed(self):
  self.status.side_effect=[{'valid':False},{'valid':False},{'valid':True},{'valid':True}]
  _,meta=self.run_guard();self.assertEqual(meta['attempt'],1)
  self.assertEqual(self.grab.call_count,1);self.root.lift.assert_called_once()
 def test_contaminated_image_is_retained_before_retry(self):
  self.status.side_effect=[{'valid':True},{'valid':False},{'valid':True},{'valid':True}]
  self.run_guard();self.assertEqual(self.grab.call_count,2)
  self.assertTrue((self.scope['out']/'case_sample0_attempt0.png').exists())
  self.assertTrue((self.scope['out']/'case_sample0_attempt1.png').exists())
  self.assertEqual(len(self.scope['report']['invalid_attempts']),1)
 def test_permanent_occlusion_fails_after_three_attempts(self):
  self.status.return_value={'valid':False}
  with self.assertRaisesRegex(RuntimeError,'after 3 attempts'):self.run_guard()
  self.assertEqual(len(self.scope['report']['invalid_attempts']),3)
  self.grab.assert_not_called()
 def test_different_valid_pixels_do_not_trigger_retry(self):
  self.status.return_value={'valid':True}
  self.grab.side_effect=[Image.new('RGB',(4,4),'red'),Image.new('RGB',(4,4),'blue')]
  a,_=self.run_guard();b,_=self.run_guard()
  self.assertNotEqual(a.tobytes(),b.tobytes());self.assertEqual(self.grab.call_count,2)
  self.root.lift.assert_not_called()
if __name__=='__main__':unittest.main(verbosity=2)
