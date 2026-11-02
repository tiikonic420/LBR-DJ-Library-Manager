"""Called only by the dedicated installation test, never by the application."""
import sys,wave
from pathlib import Path
source=Path(sys.argv[1]);profile=Path(sys.argv[2])
sys.path.insert(0,str(source))
from reliability import BackupStore,digest
audio=profile/'Morceau fictif été.wav'
with wave.open(str(audio),'wb') as stream:
    stream.setparams((1,2,44100,0,'NONE','none'));stream.writeframes(b'\0'*8820)
store=BackupStore(profile/'LBR-DJ-Library-Manager-Candidates/workspace/backups')
before=digest(audio)
identifier=store.create([audio],'Test installation : WAV fictif')
store.mark(identifier)
assert store.verify(identifier)['files'] and digest(audio)==before
print('Verified synthetic backup:',identifier)
