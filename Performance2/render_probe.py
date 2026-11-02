"""Strict borderless fixture; validated desktop capture. Application unchanged."""
import sys,os,json,time,hashlib,platform
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from PIL import ImageGrab,ImageChops
# Harness only: use physical client coordinates on Windows, before creating Tk.
dpi_result=None
if sys.platform=='win32':
 import ctypes
 try:dpi_result=bool(ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)))
 except (AttributeError,OSError):dpi_result=bool(ctypes.windll.user32.SetProcessDPIAware())
source=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(source));sys.dont_write_bytecode=True
from design_system import Skin
from manager_core import PALETTES
root=tk.Tk();root.overrideredirect(True)
# Keep the fixture away from Windows' 1x1 origin helper window.  This avoids
# an actual overlap instead of exempting a blocker or weakening the guard.
# On very small desktops, preserve the original fit-to-screen behavior.
fixture_x=min(24,max(0,root.winfo_screenwidth()-1100))
fixture_y=min(24,max(0,root.winfo_screenheight()-450))
root.geometry(f'1100x450+{fixture_x}+{fixture_y}')
root.resizable(False,False);root.style=ttk.Style(root);root.style.theme_use('clam');root.font_family='Helvetica';skin=Skin(root)
roles=['Panel.TFrame','Inset.TFrame','Warning.TFrame','TButton','Blue.TButton','Purple.TButton','Orange.TButton','Green.TButton','Nav.TButton','Active.Nav.TButton']
report={'platform':platform.platform(),'tk':root.tk.call('package','present','Tk'),'dpi_awareness_requested':dpi_result,'screen':[root.winfo_screenwidth(),root.winfo_screenheight()],'fixture_origin':[fixture_x,fixture_y],'captures':{},'capture_method':'validated desktop, borderless client; no pixel masks','invalid_attempts':[],'capture_attempts':[]}
def settle():
 root.after(120,root.quit);root.mainloop();root.update_idletasks()
def flush():
 root.update_idletasks()
 if sys.platform=='win32':
  try:ctypes.windll.dwmapi.DwmFlush()
  except (AttributeError,OSError):pass
# Native signatures are pointer-sized, including on 64-bit Windows.
if sys.platform=='win32':
 from ctypes import wintypes as wt
 u=ctypes.WinDLL('user32',use_last_error=True)
 u.GetForegroundWindow.restype=wt.HWND
 u.GetAncestor.argtypes=[wt.HWND,wt.UINT];u.GetAncestor.restype=wt.HWND
 u.GetWindowRect.argtypes=[wt.HWND,ctypes.POINTER(wt.RECT)]
 u.GetClientRect.argtypes=[wt.HWND,ctypes.POINTER(wt.RECT)]
 u.ClientToScreen.argtypes=[wt.HWND,ctypes.POINTER(wt.POINT)]
 u.GetWindowTextW.argtypes=[wt.HWND,wt.LPWSTR,ctypes.c_int]
 u.IsWindowVisible.argtypes=[wt.HWND]
 u.GetWindowThreadProcessId.argtypes=[wt.HWND,ctypes.POINTER(wt.DWORD)]
 u.SetForegroundWindow.argtypes=[wt.HWND]
 callback_type=ctypes.WINFUNCTYPE(wt.BOOL,wt.HWND,wt.LPARAM)
 u.EnumWindows.argtypes=[callback_type,wt.LPARAM]

def desktop_status(bbox):
 if sys.platform!='win32':return {'valid':True,'platform_guard':'Windows only'}
 hwnd=u.GetAncestor(root.winfo_id(),2)
 foreground=u.GetForegroundWindow()
 client=wt.RECT();origin=wt.POINT(0,0)
 coordinates_ok=bool(u.GetClientRect(hwnd,ctypes.byref(client)) and u.ClientToScreen(hwnd,ctypes.byref(origin)))
 native_bbox=[origin.x,origin.y,origin.x+client.right,origin.y+client.bottom]
 coordinates_ok=coordinates_ok and native_bbox==list(bbox)
 pid=wt.DWORD();u.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
 blockers=[];found=[]
 @callback_type
 def visit(other,_):
  if other==hwnd:found.append(True);return False
  if not u.IsWindowVisible(other):return True
  rect=wt.RECT()
  if not u.GetWindowRect(other,ctypes.byref(rect)):
   blockers.append({'hwnd':other,'error':'GetWindowRect failed'});return True
  if max(rect.left,bbox[0])<min(rect.right,bbox[2]) and max(rect.top,bbox[1])<min(rect.bottom,bbox[3]):
   title=ctypes.create_unicode_buffer(512);u.GetWindowTextW(wt.HWND(other),title,512)
   blockers.append({'hwnd':other,'title':title.value,'rect':[rect.left,rect.top,rect.right,rect.bottom]})
  return True
 u.EnumWindows(visit,0)
 return {'valid':coordinates_ok and foreground==hwnd and pid.value==os.getpid() and bool(found) and not blockers,
         'native_bbox':native_bbox,'coordinates_ok':coordinates_ok,'hwnd':hwnd,'foreground':foreground,'pid':pid.value,'found_in_z_order':bool(found),'blockers':blockers}

def guarded_grab(bbox,name,sample):
 # Retry only demonstrated contamination, never a pixel difference.
 for attempt in range(3):
  before=desktop_status(bbox)
  record={'name':name,'sample':sample,'attempt':attempt,'before':before}
  report['capture_attempts'].append(record)
  im=None
  if before['valid']:
   im=ImageGrab.grab(bbox=bbox,xdisplay=None if sys.platform=='win32' else os.environ.get('DISPLAY')).convert('RGB')
   im.save(out/f'{name}_sample{sample}_attempt{attempt}.png')
  after=desktop_status(bbox);record['after']=after
  if before['valid'] and after['valid']:return im,{'before':before,'after':after,'attempt':attempt}
  report['invalid_attempts'].append({'name':name,'sample':sample,'attempt':attempt,'before':before,'after':after})
  if attempt<2:
   root.lift();root.focus_force()
   if sys.platform=='win32':u.SetForegroundWindow(u.GetAncestor(root.winfo_id(),2))
   # Input events are not dispatched here: tested widget states stay pinned.
   time.sleep(.12);flush()
 raise RuntimeError(f'{name} sample {sample}: foreground/occlusion guard failed after 3 attempts; see capture_metadata.json')

try:
 root.lift();root.focus_force();settle()
 if sys.platform=='win32':
  # Positive control: prove that this session detects a real covering window.
  cover=tk.Toplevel(root);cover.overrideredirect(True)
  cover.geometry('120x90+100+100');cover.title('LBR capture guard positive control')
  cover.attributes('-topmost',True);cover.configure(bg='#ff00ff')
  try:
   settle();flush()
   box=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())
   control=desktop_status(box);report['occlusion_positive_control']=control
   ImageGrab.grab(bbox=box).convert('RGB').save(out/'occlusion_positive_control.png')
   cover_hwnd=u.GetAncestor(cover.winfo_id(),2)
   assert not control['valid'] and any(b['hwnd']==cover_hwnd for b in control['blockers']), 'Native occlusion positive control failed'
  finally:
   cover.destroy();root.lift();root.focus_force();u.SetForegroundWindow(u.GetAncestor(root.winfo_id(),2));settle()
 for mode in ('clair','sombre'):
  root.mode=mode;root.configure(bg=PALETTES[mode]['bg']);skin.apply(PALETTES[mode])
  # Two pages retain exact widget sizes while fitting common laptop desktops.
  for page in range(2):
   widgets=[]
   for row,role in enumerate(roles[page*5:page*5+5]):
    for col,(width,height) in enumerate(((25,25),(40,40),(87,51),(255,64),(510,73))):
     w=ttk.Frame(root,style=role) if role.endswith('TFrame') else ttk.Button(root,style=role,text='Aa')
     w.place(x=(0,35,85,182,447)[col],y=row*85,width=width,height=height);widgets.append(w)
   for state in ('normal','active','disabled','focus'):
    name=f'{mode}_{state}_{page}';images=[];meta=[]
    report['captures'][name]={'stable':False,'states_ok':False,'geometry_stable':False,'samples':meta}
    for sample in range(3):
     settle() # Process focus, Enter/Leave, mapping and compositor work first.
     for w in widgets:w.state(['!active','!disabled','!focus']+([] if state=='normal' else [state]))
     flush() # Do not dispatch input events after pinning the tested state.
     bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())
     if bbox[0]<0 or bbox[1]<0 or bbox[2]>root.winfo_screenwidth() or bbox[3]>root.winfo_screenheight():raise RuntimeError('Fixture outside visible desktop: '+str(bbox))
     before=[list(w.state()) for w in widgets]
     im,guard=guarded_grab(bbox,name,sample);im.save(out/f'{name}_sample{sample}.png');images.append(im)
     after=[list(w.state()) for w in widgets]
     geometry=[(w.winfo_reqwidth(),w.winfo_reqheight(),w.winfo_geometry()) for w in widgets]
     meta.append({'desktop_guard':guard,'bbox':bbox,'states_before':before,'states_after':after,'geometry':geometry,'sha256':hashlib.sha256(im.tobytes()).hexdigest()})
    geometry_stable=all(m['geometry']==meta[0]['geometry'] and m['bbox']==meta[0]['bbox'] for m in meta)
    stable=all(ImageChops.difference(images[0],im).getbbox() is None for im in images[1:])
    expected=set([] if state=='normal' else [state])
    states_ok=all(set(flags).intersection({'active','disabled','focus'})==expected for m in meta for side in ('states_before','states_after') for flags in m[side])
    images[0].save(out/f'{name}.png')
    (out/f'{name}.json').write_text(json.dumps(meta[0]['geometry']),encoding='utf-8')
    report['captures'][name]={'stable':stable,'states_ok':states_ok,'geometry_stable':geometry_stable,'samples':meta}
   for w in widgets:w.destroy()
except BaseException as error:
 report['error']={'type':type(error).__name__,'message':str(error)}
 raise
finally:
 (out/'capture_metadata.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');root.destroy()
assert len(report['captures'])==16
assert all(c['stable'] and c['states_ok'] and c['geometry_stable'] for c in report['captures'].values()),'Strict stabilization failed: inspect stable/states_ok/geometry_stable and all sample hashes in capture_metadata.json; no divergent sample was selected'
