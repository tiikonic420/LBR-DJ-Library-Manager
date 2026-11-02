"""Local-only installation report; no music scan and no database connection."""
import importlib,json,os,platform,sys
from pathlib import Path

def write_report():
    checks={}
    for name in ('importlib.metadata','tkinter','PIL','mutagen','rbsync.cli','pyrekordbox','sqlcipher3','numpy','sqlalchemy','psutil','greenlet'):
        try:importlib.import_module(name);checks[name]='OK'
        except Exception as exc:checks[name]=type(exc).__name__+': '+str(exc)
    data={'application':'LBR DJ Library Manager 4.0 RC2','system':platform.platform(),'python':sys.version,'components':checks}
    folder=Path(os.getenv('LOCALAPPDATA',str(Path.home())))/'LBR-DJ-Library-Manager'/'logs';folder.mkdir(parents=True,exist_ok=True)
    path=folder/'diagnostic-installation.json';path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');return path
