"""Portable Windows entry point; engine imports and configuration stay unchanged."""
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
LOG_DIR = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'LBR-DJ-Library-Manager' / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_path=LOG_DIR/'application.log'
if log_path.exists() and log_path.stat().st_size>3*1024*1024:
    for index in (2,1):
        older=LOG_DIR/f'application.log.{index}'
        if older.exists():older.replace(LOG_DIR/f'application.log.{index+1}')
    log_path.replace(LOG_DIR/'application.log.1')
log = open(LOG_DIR / 'application.log', 'a', encoding='utf-8', buffering=1)
sys.stdout = sys.stderr = log
try:
    from LBR_DJ_Library_Manager_FINAL import LBRManager
    app = LBRManager()
    app.iconbitmap(str(ROOT / 'assets' / 'lbr.ico'))
    app.mainloop()
except Exception:
    traceback.print_exc()
    import ctypes
    ctypes.windll.user32.MessageBoxW(None, 'Impossible de démarrer LBR DJ Library Manager.\n\nLe détail est enregistré ici :\n' + str(LOG_DIR / 'application.log'), 'LBR DJ Library Manager', 0x10)
    sys.exit(10)
finally:
    log.close()
