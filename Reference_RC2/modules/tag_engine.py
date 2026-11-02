"""Conservative metadata operations. DJ data is read-only."""
from pathlib import Path
import re, csv, html, shutil, datetime, xml.etree.ElementTree as ET
from mutagen import File
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON, TDRC, TRCK, TCOM, COMM, TBPM, TKEY
from mutagen.mp4 import MP4

EXTS={'.mp3','.aac','.m4a','.mp4','.flac','.wav','.aif','.aiff','.ogg','.opus','.wma','.asf','.ape','.wv','.mpc'}
FIELDS=['title','artist','album','genre','date','track','bpm','key','comment']
ID3_KEYS={'title':'TIT2','artist':'TPE1','album':'TALB','genre':'TCON','date':'TDRC','track':'TRCK','bpm':'TBPM','key':'TKEY','comment':'COMM'}
MP4_KEYS={'title':'\xa9nam','artist':'\xa9ART','album':'\xa9alb','genre':'\xa9gen','date':'\xa9day','track':'trkn','bpm':'tmpo','key':'----:com.apple.iTunes:INITIALKEY','comment':'\xa9cmt'}
VORBIS_KEYS={'title':'title','artist':'artist','album':'album','genre':'genre','date':'date','track':'tracknumber','bpm':'bpm','key':'initialkey','comment':'comment'}
ASF_KEYS={'title':'Title','artist':'Author','album':'WM/AlbumTitle','genre':'WM/Genre','date':'WM/Year','track':'WM/TrackNumber','bpm':'WM/BeatsPerMinute','key':'WM/InitialKey','comment':'Description'}

def first(x):
    if x is None: return ''
    if isinstance(x,list): return first(x[0]) if x else ''
    if isinstance(x,tuple): return str(x[0]) if x else ''
    if isinstance(x,bytes): return x.decode('utf-8','replace')
    if hasattr(x,'text'): return first(x.text)
    return str(x)

def read_tags(path):
    a=File(path, easy=False)
    if a is None: raise ValueError('Format non reconnu')
    t=a.tags
    out={k:'' for k in FIELDS}
    if t is None: return out
    if isinstance(t,ID3):
        for k,code in ID3_KEYS.items():
            frames=t.getall(code);out[k]=first(frames[0]) if frames else ''
            if frames and hasattr(frames[0],'text'):out[k]=first(frames[0].text)
    elif isinstance(a,MP4):
        for k,code in MP4_KEYS.items():out[k]=first(t.get(code))
    elif path.lower().endswith(('.wma','.asf')):
        for k,code in ASF_KEYS.items():out[k]=first(t.get(code))
    else:
        for k,code in VORBIS_KEYS.items():
            try:out[k]=first(t.get(code))
            except Exception:pass
    return out

def write_tags(path,changes):
    a=File(path,easy=False)
    if a is None:raise ValueError('Format non reconnu')
    if a.tags is None:a.add_tags()
    t=a.tags
    if isinstance(t,ID3):
        frames={'title':TIT2,'artist':TPE1,'album':TALB,'genre':TCON,'date':TDRC,'track':TRCK,'bpm':TBPM,'key':TKEY}
        for k,v in changes.items():
            if k not in FIELDS:continue
            code=ID3_KEYS[k];t.delall(code)
            if v:
                if k=='comment':t.add(COMM(encoding=3,lang='eng',desc='',text=[v]))
                else:t.add(frames[k](encoding=3,text=[v]))
        # ID3v2.3 is safest for many DJ devices; non-standard frames must survive round-trip validation.
        a.save(v2_version=3)
    elif isinstance(a,MP4):
        for k,v in changes.items():
            if k not in FIELDS:continue
            code=MP4_KEYS[k]
            if not v:t.pop(code,None);continue
            if k=='track':t[code]=[(int(str(v).split('/')[0]),0)]
            elif k=='bpm':t[code]=[int(float(v))]
            elif k=='key':t[code]=[str(v).encode('utf-8')]
            else:t[code]=[str(v)]
        a.save()
    elif path.lower().endswith(('.wma','.asf')):
        for k,v in changes.items():
            if k not in FIELDS:continue
            code=ASF_KEYS[k]
            if v:t[code]=[str(v)]
            else:t.pop(code,None)
        a.save()
    else:
        for k,v in changes.items():
            if k not in FIELDS:continue
            code=VORBIS_KEYS[k]
            if v:t[code]=[str(v)]
            else:
                try:t.pop(code,None)
                except (KeyError,AttributeError):pass
        a.save()

def safe_write(path,changes,backup_dir):
    """Back up, write, verify values, and restore original if verification fails."""
    src=Path(path); backup_dir=Path(backup_dir);backup_dir.mkdir(parents=True,exist_ok=True)
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup=backup_dir/(src.name+'.'+stamp+'.bak')
    shutil.copy2(src,backup)
    try:
        write_tags(str(src),changes)
        actual=read_tags(str(src))
        for k,v in changes.items():
            if k in FIELDS and str(actual[k]).strip()!=str(v).strip():
                if k=='track' and actual[k].split('/')[0]==str(v).split('/')[0]:continue
                raise RuntimeError(f'Vérification échouée : {k}: {actual[k]!r} != {v!r}')
    except Exception:
        shutil.copy2(backup,src)
        raise
    return str(backup)

def scan(folder):
    return [str(p) for p in Path(folder).rglob('*') if p.is_file() and p.suffix.lower() in EXTS]

def rename_pattern(tags,pattern):
    def repl(m):return str(tags.get(m.group(1).lower(),''))
    name=re.sub(r'\{(\w+)\}',repl,pattern)
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',name).strip(' .')

def parse_filename(filename,pattern):
    tokens=re.findall(r'\{(\w+)\}',pattern)
    if len(tokens)!=len(set(tokens)):raise ValueError('Champ répété dans le modèle')
    parts=re.split(r'\{\w+\}',pattern)
    regex='^'+''.join(re.escape(p)+('(?P<'+tokens[i]+'>.+?)' if i<len(tokens) else '') for i,p in enumerate(parts))+'$'
    match=re.match(regex,Path(filename).stem,re.I)
    return {k.lower():v.strip() for k,v in match.groupdict().items()} if match else None

def export_report(rows,path):
    cols=['file']+FIELDS+['serato','rekordbox']
    path=Path(path);ext=path.suffix.lower()
    if ext=='.csv':
        with path.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(rows)
    elif ext=='.html':
        head=''.join('<th>'+html.escape(c)+'</th>' for c in cols)
        body=''.join('<tr>'+''.join('<td>'+html.escape(str(row.get(c,'')))+'</td>' for c in cols)+'</tr>' for row in rows)
        path.write_text('<!doctype html><meta charset="utf-8"><title>LBR Tag Studio</title><style>body{font:14px Arial;background:#111827;color:#eee}table{border-collapse:collapse}td,th{padding:8px;border:1px solid #334155}</style><h1>LBR Tag Studio</h1><table><tr>'+head+'</tr>'+body+'</table>',encoding='utf-8')
    elif ext=='.rtf':
        def esc(s):
            return ''.join(('\\u%d?'%(ord(c) if ord(c)<32768 else ord(c)-65536)) if ord(c)>127 else ('\\'+c if c in '{}\\' else c) for c in str(s))
        lines=['{\\rtf1\\ansi\\deff0','\\b LBR Tag Studio\\b0\\par']
        for row in rows:
            lines.append('\\b '+esc(row.get('file',''))+'\\b0\\par')
            for k in cols[1:]:lines.append(esc(k+': '+str(row.get(k,'')))+'\\par')
            lines.append('\\par')
        lines.append('}');path.write_text('\n'.join(lines),encoding='ascii')
    else:raise ValueError('Format export non reconnu')

def rekordbox_xml(path):
    """Parse exported Rekordbox XML without modifying library."""
    result={}
    root=ET.parse(path).getroot()
    for tr in root.findall('.//COLLECTION/TRACK'):
        loc=tr.get('Location','')
        from urllib.parse import unquote,urlparse
        p=unquote(urlparse(loc).path) if loc.startswith('file:') else unquote(loc)
        if re.match(r'^/[A-Za-z]:',p):p=p[1:]
        cues=tr.findall('POSITION_MARK')
        hot=sum(1 for c in cues if c.get('Num') not in (None,'-1'))
        loops=sum(1 for c in cues if c.get('End') not in (None,'','0','-1'))
        result[str(Path(p)).lower()]=f'{hot} Hot / {loops} Loop (XML)'
    return result

def serato_info(path):
    """Read-only detection. Counts are deliberately not inferred from opaque blobs."""
    try:
        a=File(path,easy=False);t=a.tags
        if t is None:return 'Non détecté'
        names=[]
        if isinstance(t,ID3):
            names=[f.desc for f in t.getall('GEOB')]+[f.desc for f in t.getall('TXXX')]
        elif hasattr(t,'keys'):names=list(t.keys())
        markers=[n for n in names if 'serato' in str(n).lower() and any(z in str(n).lower() for z in ['marker','cue','loop'])]
        if markers:return 'Données DJ détectées (lecture seule)'
        return 'Non détecté'
    except Exception:return 'Non disponible'


def read_cover(path):
    import base64
    from mutagen.flac import Picture
    a=File(path,easy=False)
    if a is None or a.tags is None:return None
    if isinstance(a.tags,ID3):
        pics=a.tags.getall('APIC');return bytes(pics[0].data) if pics else None
    if isinstance(a,MP4):
        pics=a.tags.get('covr',[]);return bytes(pics[0]) if pics else None
    if hasattr(a,'pictures'):
        return bytes(a.pictures[0].data) if a.pictures else None
    pics=a.tags.get('metadata_block_picture',[]) if hasattr(a.tags,'get') else []
    return Picture(base64.b64decode(pics[0])).data if pics else None

def write_cover(path,data,mime):
    import base64
    from mutagen.id3 import APIC
    from mutagen.mp4 import MP4Cover
    from mutagen.flac import Picture
    a=File(path,easy=False)
    if a is None:raise ValueError('Format non reconnu')
    if a.tags is None:a.add_tags()
    if isinstance(a.tags,ID3):
        a.tags.delall('APIC')
        if data:a.tags.add(APIC(encoding=3,mime=mime,type=3,desc='Cover',data=data))
        a.save(v2_version=3)
    elif isinstance(a,MP4):
        if data:a.tags['covr']=[MP4Cover(data,imageformat=MP4Cover.FORMAT_PNG if mime=='image/png' else MP4Cover.FORMAT_JPEG)]
        else:a.tags.pop('covr',None)
        a.save()
    elif hasattr(a,'clear_pictures') and hasattr(a,'add_picture'):
        a.clear_pictures()
        if data:
            pic=Picture();pic.type=3;pic.mime=mime;pic.data=data;a.add_picture(pic)
        a.save()
    elif path.lower().endswith(('.ogg','.opus')):
        a.tags.pop('metadata_block_picture',None)
        if data:
            pic=Picture();pic.type=3;pic.mime=mime;pic.data=data
            a.tags['metadata_block_picture']=[base64.b64encode(pic.write()).decode('ascii')]
        a.save()
    else:raise ValueError('Pochettes non prises en charge pour ce format')

def safe_write_cover(path,data,mime,backup_dir):
    src=Path(path);backup_dir=Path(backup_dir);backup_dir.mkdir(parents=True,exist_ok=True)
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup=backup_dir/(src.name+'.'+stamp+'.bak');shutil.copy2(src,backup)
    try:
        write_cover(path,data,mime)
        if read_cover(path)!=data:raise RuntimeError('Vérification de la pochette échouée')
    except Exception:
        shutil.copy2(backup,src);raise
    return str(backup)
