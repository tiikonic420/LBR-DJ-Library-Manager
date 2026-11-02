"""MSI-only regression checks confined to a fresh GitHub-hosted runner."""
from pathlib import Path
import os,sys,subprocess,json,hashlib,ctypes,wave
assert os.environ.get('GITHUB_ACTIONS')=='true','Hosted CI only; never install on the maintainer PC'
workspace=Path(os.environ['GITHUB_WORKSPACE']).resolve()
candidate=Path(sys.argv[1]).resolve();manifest=Path(sys.argv[2]).resolve();results=Path(sys.argv[3]).resolve()
assert all(p.is_relative_to(workspace) for p in (candidate,manifest,results))
results.mkdir(exist_ok=True)
install=Path(os.environ['LOCALAPPDATA'])/'Programs/LBR Software/LBR DJ Library Manager R10 ICE1'
assert not install.exists(),'Never overwrite a pre-existing installation'
index=json.loads(manifest.read_text(encoding='utf8'))['file_index']
checks=[];errors=[];installed=False
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run_msi(args,name):
    cmd=[str(Path(os.environ['WINDIR'])/'System32/msiexec.exe')]+args+['/qn','/norestart','/L*v',str(results/(name+'.log'))]
    result=subprocess.run(cmd,timeout=240,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0,(name,result.returncode)
    checks.append(name+' returned 0')
def verify_files():
    for x in index:assert sha(install/x['relative'])==x['sha256'],x['relative']
    checks.append(str(len(index))+' installed payload hashes conform')
fake=results/'Profil_fictif_ete';fake.mkdir();sentinel=fake/'sauvegarde_fictive.bin';sentinel.write_bytes(b'LBR SYNTHETIC BACKUP SENTINEL')
try:
    run_msi(['/i',str(candidate)],'installation');installed=True;verify_files()
    # Verify backup and restoration using the actual newly installed modules.
    child="""from pathlib import Path
import sys,wave
app=Path(sys.argv[1]);profile=Path(sys.argv[2]);sys.path.insert(0,str(app/'_internal/app'))
from reliability import BackupStore
music=profile/'Musique_fictive';music.mkdir();p=music/'Essai.wav'
with wave.open(str(p),'wb') as w:w.setparams((1,2,44100,0,'NONE','none'));w.writeframes(b'\\0'*88200)
original=p.read_bytes();store=BackupStore(profile/'Sauvegardes_fictives');ident=store.create([p],'Fictitious installer regression');p.write_bytes(original+b'TEST');store.mark(ident);assert store.verify(ident)['files'];assert store.restore(ident)==1 and p.read_bytes()==original
"""
    script=results/'backup_regression.py';script.write_text(child,encoding='utf8')
    subprocess.run([str(install/'_internal/python/python.exe'),'-I','-B',str(script),str(install),str(fake)],check=True,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
    checks.append('installed BackupStore verify and byte-exact restoration passed')
    # Remove only an installed application icon in this disposable runner; /fa must restore it.
    icon=install/'_internal/app/assets/lbr.ico';icon.unlink()
    run_msi(['/fa',str(candidate)],'repair');verify_files()
    checks.append('forced repair restored a missing installed file')
    assert not list(install.rglob('*.pyc')),'Unexpected generated installation cache'
    frozen={str(p.relative_to(fake)):sha(p) for p in fake.rglob('*') if p.is_file()}
finally:
    if installed:
        try:run_msi(['/x',str(candidate)],'uninstallation')
        except Exception as e:errors.append(str(e))
if not errors:
    assert not install.exists(),'Installation directory remains'
    assert all(sha(fake/name)==digest for name,digest in frozen.items()),'Fictitious backup/profile changed'
    # Query actual Windows special folders instead of guessing redirected locations.
    paths=[]
    for csidl in (0x10,0x02):
        b=ctypes.create_unicode_buffer(32768);assert ctypes.windll.shell32.SHGetFolderPathW(None,csidl,None,0,b)==0;paths.append(Path(b.value))
    assert not (paths[0]/'LBR DJ Library Manager R10 ICE1.lnk').exists()
    assert not (paths[1]/'LBR Software R10 ICE1').exists()
    checks.extend(['installation directory and candidate shortcuts removed','fictitious backups/profile byte hashes preserved'])
report={'candidate_sha256':sha(candidate),'checks':checks,'errors':errors,'status':'passed' if not errors else 'failed','GUI_launch_tested':False,'private_music_access':False}
(results/'INSTALLATION_REGRESSION.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report));assert not errors
