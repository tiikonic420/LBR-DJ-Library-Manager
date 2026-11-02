import re
import os, sys, json, shutil, subprocess, tempfile, threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP = "RekordSync by LBR"
VERSION="5.0.6 LAPTOP"
AUDIO_EXTS = {".mp3",".wav",".flac",".aiff",".aif",".m4a",".aac",".ogg"}
CFG_DIR = Path(os.getenv("APPDATA", Path.home())) / "LBR-Rekordbox-Sync"
CFG = CFG_DIR / "v2.json"
WORK = CFG_DIR / "generated-playlists"

def load_cfg():
    try: return json.loads(CFG.read_text(encoding="utf-8"))
    except Exception: return {}

def save_cfg(d):
    CFG_DIR.mkdir(parents=True, exist_ok=True)
    CFG.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

def bundled_python():
    runtime=Path(__file__).resolve().parents[2]/'python'
    exe=runtime/'python.exe'
    return exe if exe.is_file() and (runtime/'Lib/site-packages/rbsync/cli.py').is_file() else None

def run_process(*args,**kwargs):
    if os.name=='nt':kwargs.setdefault('creationflags',subprocess.CREATE_NO_WINDOW)
    return subprocess.run(*args,**kwargs)

def find_rbsync():
    bundled=Path(__file__).resolve().parent.parent/'rbsync_entry.py'
    if bundled_python() and bundled.is_file():return str(bundled)
    candidates = [
        str(Path(os.getenv("LOCALAPPDATA","")) / "rbsync" / "venv313" / "Scripts" / "rbsync.exe"),
        shutil.which("rbsync"),
        str(Path(os.getenv("LOCALAPPDATA","")) / "rbsync" / "bin" / "rbsync.exe"),
        str(Path(os.getenv("LOCALAPPDATA","")) / "rbsync" / "bin" / "rbsync.cmd"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None

def ps_quote(s):
    return "'" + str(s).replace("'", "''") + "'"

def write_m3u8(folder: Path, out: Path):
    files = sorted(
        (p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXTS),
        key=lambda p: str(p).casefold()
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["#EXTM3U", f"#PLAYLIST:{folder.name}"] + [str(p.resolve()) for p in files]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return len(files)

def rekordbox_exe():
    guesses = [
        Path(os.getenv("PROGRAMFILES",""))/"rekordbox"/"rekordbox.exe",
        Path(os.getenv("PROGRAMFILES",""))/"Pioneer"/"rekordbox"/"rekordbox.exe",
        Path(os.getenv("LOCALAPPDATA",""))/"rekordbox"/"rekordbox.exe",
    ]
    for g in guesses:
        if g.exists(): return g
    return None

def import_batch_file(source: Path):
    """Create one M3U8 containing every source track.
    Rekordbox's own import is then used so it creates/analyzes Collection entries."""
    out = WORK / "_LBR_IMPORT_COLLECTION.m3u8"
    files = sorted(
        (p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXTS),
        key=lambda p: str(p).casefold()
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("#EXTM3U\n#PLAYLIST:LBR IMPORT COLLECTION\n" +
                   "\n".join(str(x.resolve()) for x in files) + "\n",
                   encoding="utf-8-sig")
    return out, len(files)


def parse_change_counts(text):
    import re
    def grab(pattern):
        m=re.search(pattern,text,re.I|re.M)
        return int(m.group(1)) if m else 0
    return {
        "add": grab(r"^\s*\+ add\s+(\d+)"),
        "remove": grab(r"^\s*- remove\s+(\d+)"),
        "unchanged": grab(r"^\s*= unchanged\s+(\d+)")
    }

def parse_plan_titles(text):
    """Extrait les titres détaillés listés par rbsync sous + add / - remove."""
    added=[]
    removed=[]
    section=None
    for raw in text.splitlines():
        line=raw.strip()
        low=line.lower()
        if re.match(r"^\+\s*add\s+\d+", line, re.I):
            section="add"
            continue
        if re.match(r"^-\s*remove\s+\d+", line, re.I):
            section="remove"
            continue
        if re.match(r"^=\s*unchanged\s+\d+", line, re.I) or line.startswith("SUMMARY:") or line.startswith("Dry run"):
            section=None
            continue
        if section=="add" and line.startswith("+ "):
            added.append(line[2:].strip())
        elif section=="remove" and line.startswith("- "):
            removed.append(line[2:].strip())
    return added,removed

def format_title_details(added, removed):
    lines=[]
    if added:
        lines.append("TITRES À AJOUTER :")
        lines.extend("  + "+x for x in added)
    if removed:
        if lines: lines.append("")
        lines.append("TITRES À RETIRER DE LA PLAYLIST :")
        lines.extend("  - "+x for x in removed)
    return "\n".join(lines)

def parse_missing_from_plan(text):
    missing=[]
    capture=False
    for raw in text.splitlines():
        line=raw.strip()
        if line.startswith("NOT IN YOUR REKORDBOX COLLECTION"):
            capture=True
            continue
        if capture:
            if line.startswith("SUMMARY:") or line.startswith("Dry run"):
                capture=False
            elif line.startswith("? "):
                missing.append(line[2:].strip())
    return missing

def resolve_audio_path(raw):
    """Résout un chemin rbsync vers le vrai fichier Windows sans modifier le fichier."""
    import unicodedata
    txt=str(raw or "").strip().strip('"')
    # rbsync peut imprimer des chemins avec / même sous Windows.
    txt=txt.replace("/", os.sep).replace("\\", os.sep)
    p=Path(txt)
    if p.is_file():
        return p.resolve()
    parent=p.parent
    if parent.is_dir():
        wanted=unicodedata.normalize("NFC",p.name).casefold()
        for candidate in parent.iterdir():
            if candidate.is_file() and unicodedata.normalize("NFC",candidate.name).casefold()==wanted:
                return candidate.resolve()
    return p

def rb_running():
    cp=run_process(["powershell.exe","-NoProfile","-Command",
        "(Get-Process rekordbox -ErrorAction SilentlyContinue | Measure-Object).Count"],
        capture_output=True,text=True,encoding="utf-8",errors="replace")
    return (cp.stdout or "").strip() not in ("","0")

def locate_rekordbox():
    bases=[Path(os.getenv("PROGRAMFILES","")),Path(os.getenv("LOCALAPPDATA",""))]
    guesses=[]
    for b in bases:
        guesses += [b/"rekordbox"/"rekordbox.exe", b/"Pioneer"/"rekordbox"/"rekordbox.exe",
                    b/"AlphaTheta"/"rekordbox"/"rekordbox.exe"]
    for g in guesses:
        if g.exists(): return g
    return None

def rbsync_python():
    if bundled_python():return bundled_python()
    base=Path(os.getenv("LOCALAPPDATA",""))/"rbsync"
    for env_name in ("venv313", "venv"):
        p=base/env_name/"Scripts"/"python.exe"
        if p.is_file() and (base/env_name/"Lib"/"site-packages"/"rbsync"/"cli.py").is_file():
            return p
    return None

def master_db_path():
    return Path(os.getenv("APPDATA",""))/"Pioneer"/"rekordbox"/"master.db"

def backup_master_db():
    db=master_db_path()
    if not db.exists():
        raise FileNotFoundError(f"master.db introuvable : {db}")
    from datetime import datetime
    bdir=Path.home()/"Documents"/"LBR-Rekordbox-Sync"/"backups"
    bdir.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    copied=[]
    for candidate in [db, Path(str(db)+"-wal"), Path(str(db)+"-shm")]:
        if candidate.exists():
            target=bdir/f"{candidate.name}.{stamp}.bak"
            shutil.copy2(candidate,target)
            copied.append(str(target))
    return copied

def add_missing_to_collection(files):
    """Ajoute les fichiers à djmdContent avec l'API publique pyrekordbox.
    Rekordbox doit être fermé. Un backup est fait avant cet appel.
    """
    if rb_running():
        return 30,"BLOQUÉ : Rekordbox est encore ouvert. Ferme-le complètement puis réessaie."

    py=rbsync_python()
    if not py:
        return 31,"Python de rbsync introuvable. Lance d'abord « Installer rbsync »."

    valid=[]
    invalid=[]
    for x in files:
        p=resolve_audio_path(x)
        if p.is_file():
            valid.append(str(p))
        else:
            invalid.append({"path":str(x),"error":"Fichier introuvable ou inaccessible au moment de l'ajout."})

    # Un fichier absent/inaccessible est un problème individuel, pas une panne du moteur.
    if not valid:
        out=["RÉSULTAT : 0 ajouté(s), 0 déjà présent(s), %d erreur(s)." % len(invalid)]
        for item in invalid:
            out.append("FAILED_FILE_JSON:"+json.dumps(item,ensure_ascii=False))
        return 0,"\n".join(out)

    CFG_DIR.mkdir(parents=True,exist_ok=True)
    manifest=CFG_DIR/"missing-to-collection.json"
    manifest.write_text(json.dumps(valid,ensure_ascii=False,indent=2),encoding="utf-8")

    script=CFG_DIR/"add_to_collection.py"
    script.write_text(r"""
import json, sys, re
from pathlib import Path
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass
try:
    from pyrekordbox import Rekordbox6Database
except ImportError:
    from pyrekordbox import MasterDatabase as Rekordbox6Database
try:
    from mutagen import File as MutagenFile
except ImportError:
    print("ERREUR : Mutagen absent. Relance INSTALLER_REKORDSYNC.bat.")
    sys.exit(42)

def first(tags, keys):
    for k in keys:
        v=tags.get(k) if tags else None
        if v:
            if isinstance(v,(list,tuple)): v=v[0] if v else ""
            v=str(v).strip()
            if v:return v
    return ""

def num(v):
    m=re.search(r"\d+",str(v or ""))
    return int(m.group()) if m else None

def existing_or_add(getter,adder,name):
    if not name:return None
    try:
        q=getter(Name=name)
        obj=q.one_or_none() if hasattr(q,"one_or_none") else q.first()
    except Exception: obj=None
    if obj is not None:return obj
    try:return adder(name)
    except ValueError:
        try:return getter(Name=name).first()
        except Exception:return None

def tags_for(p):
    d={"title":p.stem,"artist":"","album":"","genre":"","year":None,"track":None,"comment":""}
    try:
        audio=MutagenFile(str(p),easy=True)
        tags=getattr(audio,"tags",None) if audio else None
        if tags:
            d["title"]=first(tags,("title",)) or p.stem
            d["artist"]=first(tags,("artist","albumartist"))
            d["album"]=first(tags,("album",))
            d["genre"]=first(tags,("genre",))
            d["year"]=num(first(tags,("date","year")))
            d["track"]=num(first(tags,("tracknumber",)))
            d["comment"]=first(tags,("comment","description"))
    except Exception as e:
        print("AVERTISSEMENT TAGS :",p.name,"-",e)
    return d

files=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
db=Rekordbox6Database()
added=skipped=0
errors=[]
try:
    existing={str(getattr(c,"FolderPath","") or "").replace("\\","/").casefold() for c in db.get_content()}
    for raw in files:
        p=Path(raw); norm=str(p).replace("\\","/").casefold()
        try:
            # Ne jamais écraser les métadonnées Rekordbox d'un titre déjà présent.
            if norm in existing:
                skipped+=1
                print("DÉJÀ PRÉSENT — MÉTADONNÉES CONSERVÉES :",p)
                continue
            m=tags_for(p)
            kw={"Title":m["title"]}
            if m["year"] is not None:kw["ReleaseYear"]=m["year"]
            if m["track"] is not None:kw["TrackNo"]=m["track"]
            if m["comment"]:kw["Commnt"]=m["comment"]
            c=db.add_content(str(p),**kw)
            artist=existing_or_add(db.get_artist,db.add_artist,m["artist"])
            if artist is not None:c.ArtistID=artist.ID
            album=existing_or_add(db.get_album,db.add_album,m["album"])
            if album is not None:c.AlbumID=album.ID
            genre=existing_or_add(db.get_genre,db.add_genre,m["genre"])
            if genre is not None:c.GenreID=genre.ID
            added+=1;existing.add(norm)
            print("AJOUT + TAGS :",p.name,"|",m["title"],"|",m["artist"] or "-","|",m["album"] or "-","|",m["genre"] or "-","|",m["year"] or "-")
        except Exception as e:
            if isinstance(e,ValueError) and ("same path" in str(e).lower() or "already" in str(e).lower()):
                skipped+=1;print("DÉJÀ PRÉSENT — MÉTADONNÉES CONSERVÉES :",p)
            else:
                errors.append((str(p),str(e)));print("ERREUR :",p,e)
    db.commit()
finally:
    db.close()
print(f"RÉSULTAT : {added} ajouté(s), {skipped} déjà présent(s), {len(errors)} erreur(s).")
for path,msg in errors:
    print("FAILED_FILE_JSON:"+json.dumps({"path":path,"error":msg},ensure_ascii=False))
sys.exit(0)
""",encoding="utf-8")

    cp=run_process([str(py),str(script),str(manifest)],
                      capture_output=True,text=True,encoding="utf-8",errors="replace")
    out=(cp.stdout or "")+(("\n"+cp.stderr) if cp.stderr else "")
    if invalid:
        extra=[]
        for item in invalid:
            extra.append("FAILED_FILE_JSON:"+json.dumps(item,ensure_ascii=False))
        out=(out.rstrip()+"\n"+"\n".join(extra)).strip()
    return cp.returncode,out.strip()

def cleanup_collection_candidates(paths):
    """Retire de la Collection les titres retirés des playlists synchronisées
    s'ils ne figurent plus dans aucune playlist Rekordbox.
    Ouvre une nouvelle connexion DB après rbsync pour éviter les relations obsolètes.
    Ne supprime jamais le fichier audio physique.
    """
    if rb_running():
        return 40,"BLOQUÉ : Rekordbox doit être fermé."

    py=rbsync_python()
    if not py:
        return 41,"Python de rbsync introuvable."

    paths=sorted({str(Path(x)) for x in paths},key=str.casefold)
    if not paths:
        return 0,"Aucun morceau supprimé à nettoyer."

    CFG_DIR.mkdir(parents=True,exist_ok=True)
    manifest=CFG_DIR/"removed-from-windows.json"
    manifest.write_text(json.dumps(paths,ensure_ascii=False,indent=2),encoding="utf-8")
    script=CFG_DIR/"cleanup_collection.py"
    script.write_text(r"""
import json,sys,gc
from pathlib import Path
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass
from pyrekordbox import Rekordbox6Database

def normpath(x):
    return str(x or "").replace("\\","/").casefold()

wanted={normpath(x) for x in json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))}

# IMPORTANT : nouvelle connexion après l'apply rbsync.
gc.collect()
db=Rekordbox6Database()
deleted=kept=notfound=0
try:
    contents=list(db.get_content())
    bypath={normpath(getattr(c,"FolderPath","")):c for c in contents}

    # Construit les références restantes depuis les playlists actuellement présentes.
    # get_playlist_songs(playlist=...) est privilégié car la lecture globale de la
    # table relationnelle peut inclure des lignes obsolètes selon pyrekordbox/rbsync.
    referenced=set()
    used_by={}
    playlists=[]
    try:
        playlists=list(db.get_playlist())
    except Exception:
        playlists=[]

    membership_ok=False
    for pl in playlists:
        a=getattr(pl,"Attribute",None)
        if str(a) in ("1","PlaylistFolder") or a==1:
            continue
        pid=getattr(pl,"ID",None)
        rows=None
        # Compatibilité pyrekordbox : essayer les signatures disponibles.
        for args,kwargs in [
            ((pl,),{}),
            ((pid,),{}) if pid is not None else ((pl,),{}),
            ((),{"playlist":pl}),
            ((),{"playlist_id":pid}) if pid is not None else ((),{"playlist":pl}),
        ]:
            try:
                rows=list(db.get_playlist_songs(*args,**kwargs))
                membership_ok=True
                break
            except (TypeError,AttributeError):
                rows=None
            except Exception:
                rows=None
        if rows is None:
            continue
        for r in rows:
            # Certaines versions renvoient une relation, d'autres directement le contenu.
            cid=None
            for attr in ("ContentID","ContentId","content_id","ID"):
                v=getattr(r,attr,None)
                if v is not None:
                    cid=str(v); break
            if cid:
                referenced.add(cid)
                pname=str(getattr(pl,"Name","") or "(playlist sans nom)")
                used_by.setdefault(cid,[]).append(pname)

    # IMPORTANT V5.0.4:
    # Ne jamais utiliser la lecture globale get_playlist_songs() comme preuve
    # qu'un titre est encore utilisé. Avec rbsync/pyrekordbox elle peut contenir
    # des relations supprimées qui ne sont rattachables à aucune playlist active.
    # Seules les appartenances identifiées via une playlist précise protègent le titre.

    for norm in sorted(wanted):
        c=bypath.get(norm)
        if c is None:
            notfound+=1
            print("DÉJÀ ABSENT :",norm)
            continue
        cid=str(getattr(c,"ID",""))
        if not membership_ok:
            print("INFO : aucune référence active attribuable à une playlist pour :",getattr(c,"Title",norm))
        if cid in referenced:
            kept+=1
            names=sorted(set(used_by.get(cid,[])),key=str.casefold)
            where=" | ".join(names) if names else "(playlist non identifiée)"
            print("CONSERVÉ :",getattr(c,"Title",norm),"→ utilisé dans :",where)
            continue
        db.delete(c)
        deleted+=1
        print("RETIRÉ DE LA COLLECTION :",getattr(c,"Title",norm))
    db.commit()
finally:
    db.close()
print(f"NETTOYAGE : {deleted} retiré(s), {kept} conservé(s), {notfound} déjà absent(s).")
""",encoding="utf-8")
    cp=run_process([str(py),str(script),str(manifest)],
                      capture_output=True,text=True,encoding="utf-8",errors="replace")
    return cp.returncode,((cp.stdout or "")+(("\n"+cp.stderr) if cp.stderr else "")).strip()


def delete_rekordbox_target(target_path, target_kind, cleanup_collection=False):
    """Supprime une playlist ou un dossier Rekordbox. Aucun fichier physique n'est supprimé."""
    if rb_running():
        return 60,"BLOQUÉ : ferme complètement Rekordbox avant la suppression."
    py=rbsync_python()
    if not py:return 61,"Python de rbsync introuvable."
    CFG_DIR.mkdir(parents=True,exist_ok=True)
    manifest=CFG_DIR/"target-to-delete.json"
    manifest.write_text(json.dumps({"path":target_path,"kind":target_kind,"cleanup":bool(cleanup_collection)},ensure_ascii=False),encoding="utf-8")
    script=CFG_DIR/"delete_rb_target.py"
    script.write_text(r"""
import json,sys
from pathlib import Path
try:sys.stdout.reconfigure(encoding="utf-8")
except Exception:pass
from pyrekordbox import Rekordbox6Database
spec=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
target=spec["path"].strip(); kind=spec["kind"]; cleanup=bool(spec.get("cleanup"))
db=Rekordbox6Database()
def is_folder(x):
    a=getattr(x,"Attribute",None)
    return str(a) in ("1","PlaylistFolder") or a==1
try:
    items=list(db.get_playlist()); byid={str(getattr(x,"ID","")):x for x in items}
    def full_path(x):
        names=[];cur=x;seen=set()
        while cur is not None:
            cid=str(getattr(cur,"ID",""))
            if cid in seen:break
            seen.add(cid); name=str(getattr(cur,"Name","") or "").strip()
            if name and name.lower() not in ("root","rootplaylist"):names.append(name)
            cur=byid.get(str(getattr(cur,"ParentID","") or ""))
        return " / ".join(reversed(names))
    selected=[x for x in items if full_path(x).casefold()==target.casefold() and (is_folder(x)==(kind=="folder"))]
    if not selected:
        print("Cible introuvable :",target);sys.exit(2)
    root=selected[0]
    rootpath=full_path(root)
    affected=[x for x in items if not is_folder(x) and (full_path(x).casefold()==rootpath.casefold() or full_path(x).casefold().startswith(rootpath.casefold()+" / "))]
    candidates=set()
    for pl in affected:
        pid=str(getattr(pl,"ID",""))
        for sp in db.get_playlist_songs():
            if str(getattr(sp,"PlaylistID",""))==pid:
                cid=str(getattr(sp,"ContentID","") or "")
                if cid:candidates.add(cid)

    # Delete deepest playlists/folders first for folder targets.
    descendants=[x for x in items if full_path(x).casefold().startswith(rootpath.casefold()+" / ")]
    for x in sorted(descendants,key=lambda q:full_path(q).count(" / "),reverse=True):
        try:db.delete_playlist(x)
        except Exception:db.delete(x)
    try:db.delete_playlist(root)
    except Exception:db.delete(root)
    db.commit()
    print(("DOSSIER" if kind=="folder" else "PLAYLIST")+" SUPPRIMÉ(E) :",target)

    deleted=kept=0
    if cleanup and candidates:
        referenced={str(getattr(sp,"ContentID","") or "") for sp in db.get_playlist_songs()}
        contents={str(getattr(c,"ID","")):c for c in db.get_content()}
        for cid in candidates:
            c=contents.get(cid)
            if c is None:continue
            if cid in referenced:
                kept+=1;print("COLLECTION CONSERVÉE (utilisé ailleurs) :",getattr(c,"Title",cid));continue
            db.delete(c);deleted+=1;print("RETIRÉ DE LA COLLECTION :",getattr(c,"Title",cid))
        db.commit()
    print(f"COLLECTION : {deleted} retiré(s), {kept} conservé(s) car utilisé(s) ailleurs.")
finally:db.close()
""",encoding="utf-8")
    cp=run_process([str(py),str(script),str(manifest)],capture_output=True,text=True,encoding="utf-8",errors="replace")
    return cp.returncode,((cp.stdout or "")+(("\n"+cp.stderr) if cp.stderr else "")).strip()

def ensure_rekordbox_structure(root_name, playlist_names):
    """Create a Rekordbox playlist folder and missing child playlists.
    Uses pyrekordbox's public playlist creation API and backs up master.db first.
    """
    if rb_running():
        return 50, "BLOQUÉ : Rekordbox doit être fermé.", []
    py=rbsync_python()
    if not py:
        return 51, "Python de rbsync introuvable.", []

    root_name=(root_name or "").strip()
    names=sorted({str(x).strip() for x in playlist_names if str(x).strip()}, key=str.casefold)
    if not root_name:
        return 52, "Nom du dossier Rekordbox vide.", []

    CFG_DIR.mkdir(parents=True,exist_ok=True)
    manifest=CFG_DIR/"structure-to-create.json"
    manifest.write_text(json.dumps({"root":root_name,"playlists":names},ensure_ascii=False,indent=2),
                        encoding="utf-8")
    script=CFG_DIR/"create_rb_structure.py"
    script.write_text(r"""
import json,sys,inspect
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
from pyrekordbox import Rekordbox6Database

spec=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
root=spec["root"].strip()
wanted=spec["playlists"]
db=Rekordbox6Database()

def attr_is_folder(x):
    a=getattr(x,"Attribute",None)
    return str(a) in ("1","PlaylistFolder") or a == 1

def create_folder(name,parent=None):
    # pyrekordbox versions have used these public APIs/signatures.
    for meth in ("create_playlist_folder","add_playlist_folder"):
        fn=getattr(db,meth,None)
        if fn:
            for args,kwargs in [
                ((name,),{}),
                ((name,parent),{}) if parent is not None else ((name,),{}),
                ((),{"name":name,"parent":parent}) if parent is not None else ((),{"name":name}),
                ((),{"Name":name,"Parent":parent}) if parent is not None else ((),{"Name":name}),
            ]:
                try:return fn(*args,**kwargs)
                except TypeError:pass
    fn=getattr(db,"create_playlist",None)
    if fn:
        for args,kwargs in [
            ((name,),{"folder":True}),
            ((name,),{"is_folder":True}),
            ((name,),{"playlist_folder":True}),
        ]:
            try:return fn(*args,**kwargs)
            except TypeError:pass
    raise RuntimeError("Cette version de pyrekordbox n'expose pas la création de dossier playlist.")

def create_playlist(name,parent):
    for meth in ("create_playlist","add_playlist"):
        fn=getattr(db,meth,None)
        if not fn:continue
        pid=getattr(parent,"ID",parent)
        for args,kwargs in [
            ((name,),{"parent":parent}),
            ((name,parent),{}),
            ((name,),{"parent_id":pid}),
            ((),{"name":name,"parent":parent}),
            ((),{"Name":name,"ParentID":pid}),
        ]:
            try:return fn(*args,**kwargs)
            except TypeError:pass
    raise RuntimeError("Cette version de pyrekordbox n'expose pas la création de playlist.")

created=[]
try:
    items=list(db.get_playlist())
    roots=[x for x in items if str(getattr(x,"Name","") or "").casefold()==root.casefold() and attr_is_folder(x)]
    if roots:
        folder=roots[0]
        print("DOSSIER_EXISTANT="+root)
    else:
        folder=create_folder(root)
        db.commit()
        created.append("📁 "+root)
        print("DOSSIER_CREE="+root)

    # Refresh after folder creation.
    items=list(db.get_playlist())
    folder_id=str(getattr(folder,"ID",""))
    existing=set()
    for x in items:
        if attr_is_folder(x):continue
        if str(getattr(x,"ParentID","") or "")==folder_id:
            existing.add(str(getattr(x,"Name","") or "").casefold())

    for name in wanted:
        if name.casefold() in existing:
            print("PLAYLIST_EXISTANTE="+name)
            continue
        create_playlist(name,folder)
        db.commit()
        created.append("♫ "+root+" / "+name)
        print("PLAYLIST_CREE="+name)
finally:
    db.close()
print("CREATED_COUNT="+str(len(created)))
""",encoding="utf-8")
    cp=run_process([str(py),str(script),str(manifest)],capture_output=True,text=True,
                      encoding="utf-8",errors="replace")
    out=(cp.stdout or "")+(("\n"+cp.stderr) if cp.stderr else "")
    created=[x.split("=",1)[1] for x in out.splitlines()
             if x.startswith(("DOSSIER_CREE=","PLAYLIST_CREE="))]
    return cp.returncode,out.strip(),created

class App(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        cfg = load_cfg()
        self.source = tk.StringVar(value=cfg.get("source",""))
        self.rb_folder = tk.StringVar(value=cfg.get("rb_folder","MUSIC 2026"))
        self.status = tk.StringVar(value="Prêt • Rekordbox doit être fermé pour synchroniser.")
        self.rows = {}
        self.row_names = {}
        self.missing_files = []
        self.rb_targets = {}
        self._rb_read_failed = True
        self.playlist_selected = {}
        self.change_details = {}
        self.remove_from_playlists = tk.BooleanVar(value=False)
        self.remove_from_collection = tk.BooleanVar(value=False)
        self.build()
        self.after(250,self.refresh_rb_folders)
        if self.source.get().strip() and Path(self.source.get().strip()).is_dir():
            self.after(350,self.scan)

    def build(self):
        from integrated_ui import build_rekord
        build_rekord(self)

    def toggle_log(self):
        if self.log_visible:
            self.logcard.pack_forget()
            self.logbody.pack_forget()
            try:self.tree.configure(height=9)
            except Exception:pass
            self.log_toggle_btn.configure(text="Journal technique ▼")
            self.log_visible=False
        else:
            # Reserve real screen space for the journal instead of pushing controls below the window.
            try:self.tree.configure(height=4)
            except Exception:pass
            self.logcard.pack(fill="x",before=self.log_toggle_btn.master,pady=(0,6))
            self.logbody.pack(fill="x")
            self.log_toggle_btn.configure(text="Journal technique ▲")
            self.log_visible=True
            self.after_idle(lambda: self.log.see("end"))

    def delete_selected_target(self):
        kind,target=self.selected_rb_target()
        if kind not in ("playlist","folder"):
            messagebox.showinfo(APP,"Sélectionne une playlist (♫) ou un dossier (📁) Rekordbox dans la liste du haut.")
            return
        if rb_running():
            messagebox.showwarning(APP,"Ferme complètement Rekordbox avant la suppression.");return
        label="dossier" if kind=="folder" else "playlist"
        leaf=target.split(" / ")[-1]
        choice=messagebox.askyesnocancel(APP,
            f"Supprimer le {label} « {leaf} » ?\n\n"
            "OUI = supprimer + retirer de la Collection les titres qui ne sont utilisés dans aucune autre playlist.\n\n"
            "NON = supprimer uniquement la structure Rekordbox, Collection inchangée.\n\n"
            "ANNULER = ne rien faire.\n\n"
            + ("ATTENTION : toutes les playlists contenues dans ce dossier seront supprimées.\n\n" if kind=="folder" else "")
            + "Aucun fichier audio du disque ne sera supprimé.")
        if choice is None:return
        try:
            backups=backup_master_db()
            self.append("\n=== SUPPRESSION REKORDBOX ===")
            for x in backups:self.append("Backup : "+x)
            code,out=delete_rekordbox_target(target,kind,bool(choice));self.append(out)
            if code:
                if not self.log_visible:self.toggle_log()
                messagebox.showerror(APP,"Impossible de supprimer la cible.\n\n"+out);return
            self.refresh_rb_folders();self.scan()
            messagebox.showinfo(APP,f"{label.capitalize()} « {leaf} » supprimé(e).\n\nAucun fichier audio du disque n'a été supprimé.")
        except Exception as e:
            self.append("\nERREUR SUPPRESSION : "+str(e))
            if not self.log_visible:self.toggle_log()
            messagebox.showerror(APP,"Erreur pendant la suppression :\n\n"+str(e))

    def _store_change_details(self, name, added, removed):
        self.change_details[name] = {
            "added": list(added or []),
            "removed": list(removed or []),
        }

    def on_playlist_double_click(self, event):
        iid=self.tree.identify_row(event.y)
        if not iid:return
        self.tree.selection_set(iid)
        self.show_selected_changes()

    def show_selected_changes(self):
        sel=self.tree.selection()
        if not sel:
            messagebox.showinfo(APP,"Sélectionne une playlist puis clique sur « Voir les changements ». ")
            return
        iid=sel[0]
        name=self._row_name(iid)
        data=self.change_details.get(name,{"added":[],"removed":[]})
        added=data.get("added",[]); removed=data.get("removed",[])

        win=tk.Toplevel(self)
        win.title(f"Détails des changements — {name}")
        win.geometry("820x560")
        win.minsize(620,420)
        win.configure(bg="#0b0d12")
        win.transient(self)

        outer=ttk.Frame(win,style="App.TFrame",padding=16)
        outer.pack(fill="both",expand=True)
        ttk.Label(outer,text=name,style="Section.TLabel").pack(anchor="w")
        ttk.Label(outer,text=f"{len(added)} titre(s) à ajouter • {len(removed)} titre(s) à retirer de la playlist",
                  style="Brand.TLabel").pack(anchor="w",pady=(3,12))

        pane=ttk.Panedwindow(outer,orient="horizontal")
        pane.pack(fill="both",expand=True)
        left=ttk.Frame(pane,style="Card.TFrame",padding=10)
        right=ttk.Frame(pane,style="Card.TFrame",padding=10)
        pane.add(left,weight=1); pane.add(right,weight=1)

        ttk.Label(left,text=f"À AJOUTER ({len(added)})",style="Section.TLabel").pack(anchor="w",pady=(0,6))
        la=tk.Listbox(left,bg="#0d1016",fg="#c9d1df",selectbackground="#2b3446",relief="flat",font=("Segoe UI",10))
        lsb=ttk.Scrollbar(left,orient="vertical",command=la.yview); la.configure(yscrollcommand=lsb.set)
        lsb.pack(side="right",fill="y"); la.pack(side="left",fill="both",expand=True)
        for x in added: la.insert("end",x)
        if not added: la.insert("end","Aucun titre à ajouter")

        ttk.Label(right,text=f"À RETIRER ({len(removed)})",style="Section.TLabel").pack(anchor="w",pady=(0,6))
        lr=tk.Listbox(right,bg="#0d1016",fg="#c9d1df",selectbackground="#2b3446",relief="flat",font=("Segoe UI",10))
        rsb=ttk.Scrollbar(right,orient="vertical",command=lr.yview); lr.configure(yscrollcommand=rsb.set)
        rsb.pack(side="right",fill="y"); lr.pack(side="left",fill="both",expand=True)
        for x in removed: lr.insert("end",x)
        if not removed: lr.insert("end","Aucun titre à retirer")

        ttk.Button(outer,text="Fermer",command=win.destroy,style="Tool.TButton").pack(anchor="e",pady=(10,0))
        win.grab_set()

    def selected_rb_target(self):
        raw=self.rb_folder.get().strip()
        targets=getattr(self,"rb_targets",{})
        if raw in targets:
            return targets[raw]
        if raw.startswith("📁 "):
            return ("folder",raw[2:].strip())
        if raw.startswith("♫ "):
            return ("playlist",raw[2:].strip())
        if raw.startswith("✨ Créer automatiquement :"):
            return ("auto",raw.split(":",1)[1].strip())
        return ("folder",raw)

    def on_rb_folder_changed(self,event=None):
        save_cfg({"source":self.source.get(),"rb_folder":self.rb_folder.get()})
        self.update_sync_button()

    def update_sync_button(self):
        kind,name=self.selected_rb_target()
        short=name.split(" / ")[-1] if name else ""
        if kind=="auto" and short:
            self.sync_btn.configure(text=f"✨  CRÉER & SYNCHRONISER {short}")
        else:
            self.sync_btn.configure(text=f"🔄  SYNCHRONISER {short}" if short else "🔄  SYNCHRONISER")

    def refresh_rb_folders(self):
        self._rb_read_failed=True
        self.rb_targets={}
        self.rb_combo['values']=[]
        self.sync_btn.configure(state='disabled')
        py=rbsync_python()
        if not py:
            self.rb_folder.set('')
            self.status.set("rbsync/pyrekordbox requis pour lire Rekordbox.")
            return
        CFG_DIR.mkdir(parents=True,exist_ok=True)
        script=CFG_DIR/"list_rb_tree.py"
        script.write_text("""
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
from pyrekordbox import Rekordbox6Database
db=Rekordbox6Database()
try:
    items=list(db.get_playlist())
    byid={str(getattr(x,"ID","")):x for x in items}
    def is_folder(x):
        return str(getattr(x,"Attribute","")) in ("1","PlaylistFolder")
    def full_path(x):
        names=[]; seen=set(); cur=x
        while cur is not None:
            cid=str(getattr(cur,"ID",""))
            if cid in seen: break
            seen.add(cid)
            name=str(getattr(cur,"Name","") or "").strip()
            if name and name.lower() not in ("root","rootplaylist"): names.append(name)
            cur=byid.get(str(getattr(cur,"ParentID","") or ""))
        return " / ".join(reversed(names))
    for x in items:
        name=str(getattr(x,"Name","") or "").strip()
        if not name or name.lower() in ("root","rootplaylist"): continue
        path=full_path(x)
        if path: print(("FOLDER=" if is_folder(x) else "PLAYLIST=")+path)
finally:
    db.close()
""",encoding="utf-8")
        cp=run_process([str(py),str(script)],capture_output=True,text=True,
                          encoding="utf-8",errors="replace")
        self.rb_targets={}
        if cp.returncode:
            self.rb_combo['values']=[]
            self.rb_folder.set('')
            self.sync_btn.configure(state='disabled')
            self.status.set('Lecture Rekordbox impossible : consulte le journal puis Actualiser.')
            self.append('ERREUR DE LECTURE REKORDBOX :\n'+(cp.stderr or cp.stdout or f'Code de sortie {cp.returncode}'))
            return
        self._rb_read_failed=False
        self.sync_btn.configure(state='normal')
        vals=[]
        try:
            src_name=self.source_path().name.strip()
        except Exception:
            src_name=""
        if src_name:
            auto_label="✨ Créer automatiquement : "+src_name
            vals.append(auto_label)
            self.rb_targets[auto_label]=("auto",src_name)
        for line in (cp.stdout or "").splitlines():
            if line.startswith("FOLDER="):
                path=line.split("=",1)[1].strip(); label="📁 "+path
                if label not in self.rb_targets:
                    vals.append(label); self.rb_targets[label]=("folder",path)
            elif line.startswith("PLAYLIST="):
                path=line.split("=",1)[1].strip(); label="♫ "+path
                if label not in self.rb_targets:
                    vals.append(label); self.rb_targets[label]=("playlist",path)
        vals.sort(key=lambda x:(0 if x.startswith("✨") else 1 if x.startswith("📁") else 2,x.casefold()))
        self.rb_combo["values"]=vals
        current=self.rb_folder.get().strip()
        if current not in vals:
            for label,(kind,path) in self.rb_targets.items():
                if current.casefold()==path.casefold():
                    self.rb_folder.set(label); break
            else:
                if vals:self.rb_folder.set(vals[0])
        self.update_sync_button()
        self.status.set(f"{len(vals)} élément(s) Rekordbox chargé(s)." if vals else
                        "Aucun dossier/playlist Rekordbox détecté.")

    def pick(self):
        p=filedialog.askdirectory(title="Choisir le dossier Windows à synchroniser")
        if p:
            self.source.set(p)
            if not self.rb_folder.get().strip(): self.rb_folder.set(Path(p).name)
            save_cfg({"source":p,"rb_folder":self.rb_folder.get()})
            self.scan()
        self.refresh_rb_folders()

    def append(self,s):
        self.log.insert("end",s.rstrip()+"\n"); self.log.see("end"); self.update_idletasks()

    def source_path(self):
        p=Path(self.source.get().strip())
        if not p.is_dir():
            messagebox.showerror(APP,"Choisis d'abord ton dossier MUSIC 2026.")
            return None
        return p

    def _row_name(self,iid):
        if iid in self.row_names:return self.row_names[iid]
        text=str(self.tree.item(iid,"text") or "")
        return text[2:] if text.startswith(("☑ ","☐ ")) else text

    def _paint_check(self,iid,name):
        self.tree.item(iid,text=("☑ " if self.playlist_selected.get(name,True) else "☐ ")+name)

    def on_playlist_click(self,event):
        iid=self.tree.identify_row(event.y)
        region=self.tree.identify_region(event.x,event.y)
        col=self.tree.identify_column(event.x)
        if iid and region in ("tree","cell") and col=="#0":
            name=self._row_name(iid)
            self.playlist_selected[name]=not self.playlist_selected.get(name,True)
            self._paint_check(iid,name)
            return "break"

    def on_playlist_space(self,event=None):
        for iid in self.tree.selection():
            name=self._row_name(iid)
            self.playlist_selected[name]=not self.playlist_selected.get(name,True)
            self._paint_check(iid,name)
        return "break"

    def select_all_playlists(self):
        for name,iid in self.rows.items():
            self.playlist_selected[name]=True; self._paint_check(iid,name)
        self.status.set(f"{len(self.rows)} playlist(s) sélectionnée(s).")

    def deselect_all_playlists(self):
        for name,iid in self.rows.items():
            self.playlist_selected[name]=False; self._paint_check(iid,name)
        self.status.set("Toutes les playlists sont désélectionnées.")

    def selected_made(self,made):
        chosen=[x for x in made if self.playlist_selected.get(x[0].name,True)]
        if not chosen:
            raise RuntimeError("Aucune playlist cochée. Coche au moins une playlist à analyser/synchroniser.")
        return chosen

    def scan(self):
        p=self.source_path()
        if not p:return []
        self.tree.delete(*self.tree.get_children()); self.rows={}; self.row_names={}
        result=[]
        for d in sorted((x for x in p.iterdir() if x.is_dir()),key=lambda x:x.name.casefold()):
            n=sum(1 for f in d.rglob("*") if f.is_file() and f.suffix.lower() in AUDIO_EXTS)
            if d.name not in self.playlist_selected:self.playlist_selected[d.name]=True
            iid=self.tree.insert("", "end", text=("☑ " if self.playlist_selected[d.name] else "☐ ")+d.name, values=(n,"Prêt à analyser"))
            self.rows[d.name]=iid; self.row_names[iid]=d.name; result.append((d,n))
        self.status.set(f"{len(result)} dossiers/playlist détectés.")
        save_cfg({"source":str(p),"rb_folder":self.rb_folder.get()})
        return result

    def cmd(self,args):
        exe=find_rbsync()
        if not exe: raise RuntimeError("rbsync n'est pas installé. Clique sur « Installer le moteur rbsync ».")
        command=[str(rbsync_python()),exe] if Path(exe).suffix=='.py' else [exe]
        cp=run_process(command+args,capture_output=True,text=True,encoding="utf-8",errors="replace")
        out=(cp.stdout or "") + (("\n"+cp.stderr) if cp.stderr else "")
        return cp.returncode,out.strip()

    def doctor(self):
        def job():
            try:
                self.append("=== DIAGNOSTIC RBSYNC ===")
                code,out=self.cmd(["doctor","--offline"])
                self.append(out or "(aucune sortie)")
                self.status.set("Diagnostic terminé." if code==0 else f"Diagnostic terminé avec code {code}.")
            except Exception as e:
                self.append("ERREUR: "+str(e)); messagebox.showerror(APP,str(e))
        threading.Thread(target=job,daemon=True).start()

    def generate(self):
        kind,target=self.selected_rb_target()
        WORK.mkdir(parents=True,exist_ok=True)

        if kind=="playlist":
            d=self.source_path()
            if not d:return []
            n=sum(1 for f in d.rglob("*") if f.is_file() and f.suffix.lower() in AUDIO_EXTS)
            safe=re.sub(r'[<>:"/\\|?*]+',"_",target)
            out=WORK/(safe+".m3u8")
            write_m3u8(d,out)
            self.tree.delete(*self.tree.get_children()); self.rows={}; self.row_names={}
            leaf=target.split(" / ")[-1]
            if d.name not in self.playlist_selected:self.playlist_selected[d.name]=True
            iid=self.tree.insert("","end",text=("☑ " if self.playlist_selected[d.name] else "☐ ")+leaf,values=(n,"Prêt à analyser"))
            self.rows[d.name]=iid; self.row_names[iid]=d.name
            return self.selected_made([(d,out,n)])

        rows=self.scan()

        # Création automatique d'une playlist unique :
        # si le dossier Windows contient directement les morceaux et aucun sous-dossier,
        # le dossier racine représente lui-même la playlist.
        if kind=="auto" and not rows:
            d=self.source_path()
            if not d:return []
            n=sum(1 for f in d.rglob("*") if f.is_file() and f.suffix.lower() in AUDIO_EXTS)
            if n:
                if d.name not in self.playlist_selected:self.playlist_selected[d.name]=True
                self.tree.delete(*self.tree.get_children()); self.rows={}; self.row_names={}
                iid=self.tree.insert("","end",
                    text=("☑ " if self.playlist_selected[d.name] else "☐ ")+d.name,
                    values=(n,"Prêt à créer / analyser"))
                self.rows[d.name]=iid; self.row_names[iid]=d.name
                safe=re.sub(r'[<>:"/\\|?*]+',"_",d.name)
                out=WORK/(safe+".m3u8")
                write_m3u8(d,out)
                return self.selected_made([(d,out,n)])

        made=[]
        for d,n in rows:
            if not self.playlist_selected.get(d.name,True):
                iid=self.rows.get(d.name)
                if iid:self.tree.set(iid,"state","IGNORÉ — non sélectionnée")
                continue
            out=WORK/(d.name+".m3u8")
            write_m3u8(d,out); made.append((d,out,n))
        return self.selected_made(made)

    def playlist_arg(self,name):
        kind,target=self.selected_rb_target()
        if kind=="playlist":
            return target
        return f"{target} / {name}" if target else name

    def find_removed_paths(self, made):
        """Return Collection paths currently in each matched playlist but absent from its Windows m3u."""
        py=rbsync_python()
        if not py:return []
        spec=[]
        for d,m3u,n in made:
            pl=self.playlist_arg(d.name)
            spec.append({"playlist":pl,"m3u":str(m3u)})
        f=CFG_DIR/"cleanup-spec.json"
        f.write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding="utf-8")
        script=CFG_DIR/"find_removed.py"
        script.write_text(r"""
import json,sys
from pathlib import Path
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
from pyrekordbox import Rekordbox6Database
spec=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
db=Rekordbox6Database()
def norm(x): return str(x).replace("\\","/").casefold()
try:
    for item in spec:
        desired=set()
        for line in Path(item["m3u"]).read_text(encoding="utf-8-sig",errors="replace").splitlines():
            line=line.strip()
            if line and not line.startswith("#"): desired.add(norm(line))
        parts=[x.strip() for x in item["playlist"].split("/") if x.strip()]
        pls=list(db.get_playlist())
        target=None
        # Match leaf name; rbsync already validates the full playlist path before cleanup.
        for pl in pls:
            if str(getattr(pl,"Name","")).casefold()==parts[-1].casefold():
                target=pl
        if target is None: continue
        try: songs=list(db.get_playlist_songs(PlaylistID=getattr(target,"ID")))
        except Exception:
            try: songs=list(db.get_playlist_songs(playlist=target))
            except Exception: continue
        for r in songs:
            c=getattr(r,"Content",None)
            if c is None:
                cid=getattr(r,"ContentID",None)
                try: c=db.get_content(ID=cid).one()
                except Exception: continue
            path=str(getattr(c,"FolderPath","") or "")
            if path and norm(path) not in desired:
                print("REMOVED_PATH="+path)
finally:
    db.close()
""",encoding="utf-8")
        cp=run_process([str(py),str(script),str(f)],capture_output=True,text=True,
                          encoding="utf-8",errors="replace")
        return [line.split("=",1)[1] for line in (cp.stdout or "").splitlines()
                if line.startswith("REMOVED_PATH=")]

    def m3u_without_removals(self, d, m3u):
        """If playlist removals are disabled, keep existing Rekordbox tracks in the apply M3U."""
        removed=self.find_removed_paths([(d,m3u,0)])
        if not removed:
            return m3u
        lines=Path(m3u).read_text(encoding="utf-8-sig",errors="replace").splitlines()
        existing={x.strip().replace("\\","/").casefold() for x in lines if x.strip() and not x.startswith("#")}
        for path in removed:
            norm=str(path).replace("\\","/").casefold()
            if norm not in existing:
                lines.append(str(path))
                existing.add(norm)
        out=WORK/(d.name+"__KEEP_REMOVED.m3u8")
        out.write_text("\n".join(lines)+"\n",encoding="utf-8-sig")
        return out

    def removed_titles_fallback(self, d, m3u):
        """Get removal names directly from Rekordbox when rbsync's textual plan has no title lines."""
        try:
            return [Path(x).stem for x in self.find_removed_paths([(d,m3u,0)])]
        except Exception:
            return []

    def sync_one_click(self):
        """Synchronise uniquement après une lecture réussie de Rekordbox."""
        if getattr(self,'_rb_read_failed',True):
            messagebox.showerror(APP,'La bibliothèque Rekordbox n’a pas pu être lue. Consulte le journal puis clique sur Actualiser avant de synchroniser.')
            return
        if rb_running():
            messagebox.showwarning(APP,
                "Rekordbox est ouvert.\n\nFerme-le complètement avant la synchronisation.")
            return
        if not messagebox.askyesno(APP,
            "Synchroniser automatiquement "+self.selected_rb_target()[1]+" ?\n\n"
            "LBR va :\n"
            "• analyser uniquement les playlists cochées ;\n"
            "• créer automatiquement le dossier/les playlists Rekordbox manquants ;\n"
            "• sauvegarder master.db ;\n"
            "• ajouter les nouveaux morceaux à la Collection ;\n"
            "• synchroniser uniquement les playlists cochées ;\n"
            f"• retrait des playlists : {'OUI' if self.remove_from_playlists.get() else 'NON'} ;\n"
            f"• retrait de la Collection : {'OUI' if self.remove_from_collection.get() else 'NON'} (uniquement si sûr).\n\n"
            "Aucun fichier musical ne sera supprimé.\nContinuer ?"):
            return

        def job():
            try:
                made=self.generate()
                self.missing_files=[]
                matched=[]
                missing_playlists=[]
                self.append("\n=== REKORDSYNC 5.0.6 — SYNCHRONISATION + CRÉATION AUTO : "+self.rb_folder.get()+" ===")
                self.status.set("Étape 1/6 — Analyse de la structure…")

                # 1. First pass: detect missing playlists.
                for d,m3u,n in made:
                    pl=self.playlist_arg(d.name)
                    code,out=self.cmd(["plan",str(m3u),"--playlist",pl])
                    iid=self.rows.get(d.name)
                    if "there is no playlist called" in out:
                        missing_playlists.append((d,m3u,n,pl))
                        self.append(f"\n{pl} : À CRÉER")
                        if iid:self.tree.set(iid,"state","À CRÉER")
                    else:
                        missing=parse_missing_from_plan(out)
                        self.missing_files.extend(missing)
                        matched.append((d,m3u,n,pl))
                        if iid:self.tree.set(iid,"state",
                            f"{len(missing)} nouveau(x) Collection" if missing else "Playlist trouvée")

                # 2. Create the selected Windows root folder + missing child playlists.
                if missing_playlists:
                    kind,target=self.selected_rb_target()
                    if kind not in ("folder","auto"):
                        raise RuntimeError("La création automatique concerne une cible dossier Rekordbox.")
                    self.status.set(f"Étape 2/6 — Création de {len(missing_playlists)} playlist(s)…")
                    backups=backup_master_db()
                    self.append("\nSauvegarde avant création de structure :")
                    for x in backups:self.append("  "+x)
                    root=target or self.source_path().name
                    code,out,created=ensure_rekordbox_structure(root,[d.name for d,_,_,_ in missing_playlists])
                    self.append("\n=== CRÉATION STRUCTURE REKORDBOX ===\n"+out)
                    if code:
                        raise RuntimeError("Impossible de créer automatiquement la structure Rekordbox.")
                    # Re-plan the newly created playlists.
                    for d,m3u,n,pl in missing_playlists:
                        code,out=self.cmd(["plan",str(m3u),"--playlist",pl])
                        if "there is no playlist called" in out:
                            raise RuntimeError(f"La playlist {pl} reste introuvable après sa création.")
                        missing=parse_missing_from_plan(out)
                        self.missing_files.extend(missing)
                        matched.append((d,m3u,n,pl))
                        iid=self.rows.get(d.name)
                        if iid:self.tree.set(iid,"state","CRÉÉE • prête à synchroniser")

                self.missing_files=sorted(set(self.missing_files),key=str.casefold)
                self.append(f"\nAnalyse : {len(matched)} playlist(s) prête(s), "
                            f"{len(missing_playlists)} créée(s), {len(self.missing_files)} nouveau(x) morceau(x).")

                # 2. Backup + Collection
                if self.missing_files:
                    self.status.set(f"Étape 2/4 — Ajout de {len(self.missing_files)} nouveau(x) morceau(x)…")
                    backups=backup_master_db()
                    self.append("\nSauvegarde master.db :")
                    for x in backups:self.append("  "+x)
                    code,out=add_missing_to_collection(self.missing_files)
                    self.append("\n=== AJOUT COLLECTION ===\n"+out)
                    collection_failures=[]
                    for line in (out or "").splitlines():
                        if line.startswith("FAILED_FILE_JSON:"):
                            try:
                                collection_failures.append(json.loads(line.split(":",1)[1]))
                            except Exception:
                                pass
                    if code:
                        raise RuntimeError(
                            "Impossible d'exécuter l'étape d'ajout Collection.\\n\\n"
                            f"Code retour : {code}\\n\\n" + ((out or "").strip()[-5000:])
                        )
                    if collection_failures:
                        self.append("\n⚠ TITRE(S) NON AJOUTÉ(S) — la synchronisation continue :")
                        for item in collection_failures:
                            self.append("  • "+item.get("path","?")+" — "+item.get("error","Erreur inconnue"))
                else:
                    collection_failures=[]
                    self.append("\nCollection : aucun nouveau morceau à ajouter.")

                # 3. Re-plan after Collection addition; never apply a playlist with unresolved tracks.
                self.status.set("Étape 3/4 — Vérification après ajout Collection…")
                ready=[]
                unresolved=0
                total_add=total_remove=0
                for d,m3u,n,pl in matched:
                    code,out=self.cmd(["plan",str(m3u),"--playlist",pl])
                    miss=parse_missing_from_plan(out)
                    iid=self.rows.get(d.name)
                    if miss:
                        unresolved+=len(miss)
                        self.append(f"\n{pl} : BLOQUÉ — {len(miss)} morceau(x) toujours absent(s).")
                        if iid:self.tree.set(iid,"state",f"BLOQUÉ — {len(miss)} absent(s)")
                        continue
                    counts=parse_change_counts(out)
                    added_titles,removed_titles=parse_plan_titles(out)
                    if counts["remove"] and not removed_titles:
                        removed_titles=self.removed_titles_fallback(d,m3u)
                    self._store_change_details(d.name,added_titles,removed_titles)
                    total_add+=counts["add"]; total_remove+=counts["remove"]
                    ready.append((d,m3u,n,pl,counts,added_titles,removed_titles))

                if unresolved:
                    self.append(
                        f"\n⚠ {unresolved} morceau(x) restent introuvables. "
                        "Les playlists concernées sont ignorées ; les autres seront synchronisées."
                    )
                    # Le résumé doit refléter les titres réellement non synchronisés,
                    # même si l'échec a été détecté seulement au second plan rbsync.
                    known={str(x.get("path","")).casefold() for x in collection_failures}
                    for raw in self.missing_files:
                        rp=str(resolve_audio_path(raw))
                        if rp.casefold() not in known:
                            collection_failures.append({
                                "path":rp,
                                "error":"Toujours absent de la Collection Rekordbox après tentative d'ajout."
                            })
                            known.add(rp.casefold())

                # 4. Capture candidates BEFORE playlist removal, then apply.
                removed_candidates=self.find_removed_paths([(d,m3u,n) for d,m3u,n,pl in matched])
                self.status.set("Étape 4/5 — Synchronisation des playlists…")
                synced=failures=adds=removes=0
                for d,m3u,n,pl,counts,added_titles,removed_titles in ready:
                    self.append(f"\n--- {pl} ---")
                    details=format_title_details(added_titles,removed_titles)
                    if details:
                        self.append(details)
                    apply_m3u=m3u
                    effective_remove=counts["remove"]
                    if not self.remove_from_playlists.get():
                        apply_m3u=self.m3u_without_removals(d,m3u)
                        effective_remove=0
                        if counts["remove"]:
                            self.append("RETRAIT PLAYLIST DÉSACTIVÉ — les titres ci-dessus sont conservés.")
                    code,out=self.cmd(["apply",str(apply_m3u),"--playlist",pl])
                    self.append(out)
                    iid=self.rows.get(d.name)
                    if code==0:
                        synced+=1; adds+=counts["add"]; removes+=effective_remove
                        if iid:self.tree.set(iid,"state",f"OK • +{counts['add']} / -{effective_remove}")
                    else:
                        failures+=1
                        if iid:self.tree.set(iid,"state",f"ERREUR — code {code}")

                # 5. Optional Collection cleanup after playlists are updated.
                cleaned_text="Aucun nettoyage Collection nécessaire."
                if failures==0 and removed_candidates and self.remove_from_collection.get():
                    self.status.set("Étape 5/5 — Nettoyage sécurisé de la Collection…")
                    # backup again immediately before Collection deletion
                    backups=backup_master_db()
                    self.append("\nSauvegarde avant nettoyage Collection :")
                    for x in backups:self.append("  "+x)
                    ccode,cout=cleanup_collection_candidates(removed_candidates)
                    cleaned_text=cout
                    self.append("\n=== NETTOYAGE COLLECTION ===\n"+cout)
                    if ccode:
                        failures+=1

                if removed_candidates and not self.remove_from_collection.get():
                    self.append("\nNETTOYAGE COLLECTION DÉSACTIVÉ — aucun titre retiré de la Collection.")

                cleaned_count=0
                mclean=re.search(r"NETTOYAGE\s*:\s*(\d+)\s+retiré", cleaned_text or "", re.I)
                if mclean:
                    cleaned_count=int(mclean.group(1))
                failed_tracks=len(collection_failures)
                issue_count=failures+failed_tracks+unresolved
                summary=(f"{synced} playlist(s) synchronisée(s) • {len(missing_playlists)} créée(s) • "
                         f"+{adds} / -{removes} playlist • {cleaned_count} retiré(s) Collection • "
                         f"{failed_tracks} titre(s) non ajouté(s) • {failures} erreur(s) playlist")
                self.append("\n=== TERMINÉ ===\n"+summary)
                if collection_failures:
                    self.append("\nTITRES NON SYNCHRONISÉS :")
                    for item in collection_failures:
                        self.append("  • "+Path(item.get("path","?")).name+" — "+item.get("error","Erreur inconnue"))
                self.status.set("Terminé — "+summary)
                if issue_count:
                    if not self.log_visible:
                        self.toggle_log()
                    details=""
                    if collection_failures:
                        details="\n\nTitre(s) non ajouté(s) :\n" + "\n".join(
                            "• "+Path(x.get("path","?")).name for x in collection_failures[:10]
                        )
                    messagebox.showwarning(APP,"Synchronisation terminée avec avertissement(s).\n\n"+summary+details)
                else:
                    messagebox.showinfo(APP,
                        "Synchronisation terminée avec succès.\n\n"+summary+
                        "\n\nTu peux maintenant ouvrir Rekordbox.\n"
                        "Analyse les nouveaux morceaux dans Rekordbox si nécessaire.")
            except Exception as e:
                self.append("\nERREUR V3 : "+str(e))
                self.status.set("Synchronisation interrompue — détail dans le journal.")
                self.append("\\n===== ERREUR DE SYNCHRONISATION =====\\n"+str(e)+"\\n")
                if not self.log_visible:
                    self.toggle_log()
                messagebox.showerror(APP,"Synchronisation interrompue.\\n\\n"+str(e))
        threading.Thread(target=job,daemon=True).start()

    def plan_all(self):
        kind,target=self.selected_rb_target()
        if kind=="auto":
            try:
                made=self.generate()
                self.append("\n=== ANALYSE CRÉATION AUTOMATIQUE ===")
                self.append(f"📁 {target} : sera créé s'il n'existe pas")
                for d,m3u,n in made:
                    iid=self.rows.get(d.name)
                    self.append(f"♫ {d.name} : sera créée si absente • {n} fichier(s)")
                    if iid:self.tree.set(iid,"state","À CRÉER / SYNCHRONISER")
                self.status.set(f"{len(made)} playlist(s) prête(s) pour création/synchronisation.")
            except Exception as e:
                self.append("\nERREUR ANALYSE AUTO : "+str(e))
                self.status.set("Erreur pendant l'analyse.")
            return
        def job():
            try:
                made=self.generate()
                self.missing_files=[]
                self.change_details={}
                self.append("\n=== ANALYSE MULTI-PLAYLISTS ===")
                total_add=total_remove=total_missing=matched=ignored=0

                for d,m3u,n in made:
                    pl=self.playlist_arg(d.name)
                    code,out=self.cmd(["plan",str(m3u),"--playlist",pl])
                    self.append(f"\n--- {pl} ---\n{out}")
                    added_titles,removed_titles=parse_plan_titles(out)
                    counts_preview=parse_change_counts(out)
                    if counts_preview["remove"] and not removed_titles:
                        removed_titles=self.removed_titles_fallback(d,m3u)
                    self._store_change_details(d.name,added_titles,removed_titles)
                    details=format_title_details(added_titles,removed_titles)
                    if details:
                        self.append("\n"+details)
                    iid=self.rows.get(d.name)

                    if "there is no playlist called" in out:
                        ignored+=1
                        if iid:self.tree.set(iid,"state","IGNORÉ — aucune playlist Rekordbox correspondante")
                        continue

                    matched+=1
                    missing_here=parse_missing_from_plan(out)
                    counts=parse_change_counts(out)
                    self.missing_files.extend(missing_here)
                    total_missing+=len(missing_here)
                    total_add+=counts["add"]
                    total_remove+=counts["remove"]

                    bits=[]
                    if missing_here: bits.append(f"{len(missing_here)} nouveau(x) à ajouter à la Collection")
                    if counts["add"]: bits.append(f"+{counts['add']} playlist")
                    if counts["remove"]: bits.append(f"-{counts['remove']} playlist")
                    if not bits: bits.append("À jour")
                    if iid:self.tree.set(iid,"state"," • ".join(bits))

                self.missing_files=sorted(set(self.missing_files),key=str.casefold)
                summary=(f"{len(made)} dossier(s) analysé(s) • {matched} playlist(s) trouvée(s) • "
                         f"{ignored} ignorée(s) • {len(self.missing_files)} nouveau(x) morceau(x) • "
                         f"+{total_add} / -{total_remove} changement(s) playlist")
                self.append("\n=== RÉSUMÉ GLOBAL ===\n"+summary)
                self.status.set(summary)
            except Exception as e:
                self.append("ERREUR: "+str(e)); messagebox.showerror(APP,str(e))
        threading.Thread(target=job,daemon=True).start()

    def import_collection(self):
        files=sorted(set(self.missing_files),key=str.casefold)
        if not files:
            messagebox.showinfo(APP,
                "Aucun morceau manquant mémorisé.\n\nClique d'abord sur « Analyser toutes les playlists ».")
            return

        if rb_running():
            messagebox.showwarning(APP,
                "Ferme complètement Rekordbox avant cette étape.\n\n"
                "La V2.5 écrit directement les nouveaux morceaux dans la Collection "
                "avec l'API pyrekordbox, donc la base ne doit pas être ouverte par Rekordbox.")
            return

        preview="\n".join(files[:6])
        if len(files)>6:
            preview+=f"\n… et {len(files)-6} autre(s)"

        if not messagebox.askyesno(APP,
            f"{len(files)} morceau(x) absent(s) vont être ajouté(s) à la Collection Rekordbox.\n\n"
            "Méthode : lecture des tags audio + ajout pyrekordbox dans master.db.\n"
            "Une sauvegarde de master.db sera créée AVANT l'écriture.\n\n"
            f"{preview}\n\nContinuer ?"):
            return

        self.append(f"\n=== AJOUT DIRECT À LA COLLECTION : {len(files)} MORCEAU(X) ===")

        def job():
            try:
                backups=backup_master_db()
                self.append("Sauvegarde créée :")
                for x in backups:self.append("  "+x)

                code,out=add_missing_to_collection(files)
                self.append(out or f"Code retour {code}")
                if code==0:
                    self.status.set("Morceaux ajoutés à la Collection. Relance maintenant l'analyse LBR.")
                    messagebox.showinfo(APP,
                        "Ajout à la Collection terminé.\n\n"
                        "Clique maintenant sur « Analyser toutes les playlists » SANS ouvrir Rekordbox.\n"
                        "Le morceau devrait alors être reconnu et apparaître comme « + add ».\n\n"
                        "Ensuite clique sur « Synchroniser tout » pendant que Rekordbox est toujours fermé.\n"
                        "Après la synchronisation, ouvre Rekordbox : le morceau sera dans sa playlist.\n"
                        "Les tags intégrés sont importés dès l'ajout. Rekordbox pourra ensuite analyser le morceau.")
                else:
                    self.status.set("Ajout Collection interrompu — sauvegarde conservée.")
                    messagebox.showwarning(APP,
                        "L'ajout n'a pas terminé correctement.\n"
                        "La sauvegarde de master.db a été conservée.\n\nConsulte le journal.")
            except Exception as e:
                self.append("ERREUR AJOUT COLLECTION: "+repr(e))
                messagebox.showerror(APP,f"Erreur :\n{e}")
        threading.Thread(target=job,daemon=True).start()

    def apply_all(self):
        if rb_running():
            messagebox.showwarning(APP,"Ferme complètement Rekordbox avant de synchroniser les playlists.")
            return
        if not messagebox.askyesno(APP,
            "Synchroniser TOUTES les playlists correspondantes ?\n\n"
            "Chaque sous-dossier Windows sera comparé à la playlist Rekordbox du même nom.\n"
            "Les playlists absentes seront ignorées.\n"
            "rbsync créera ses sauvegardes avant écriture.\n\nContinuer ?"):
            return

        def job():
            try:
                made=self.generate()
                self.append("\n=== SYNCHRONISATION MULTI-PLAYLISTS ===")
                failures=ignored=synced=adds=removes=0
                for d,m3u,n in made:
                    pl=self.playlist_arg(d.name)
                    iid=self.rows.get(d.name)
                    pcode,pout=self.cmd(["plan",str(m3u),"--playlist",pl])

                    if "there is no playlist called" in pout:
                        ignored+=1
                        self.append(f"\n--- {pl} : IGNORÉ (playlist absente) ---")
                        if iid:self.tree.set(iid,"state","IGNORÉ — playlist absente")
                        continue

                    missing=parse_missing_from_plan(pout)
                    if missing:
                        failures+=1
                        self.append(f"\n--- {pl} : BLOQUÉ ({len(missing)} morceau(x) absent(s) de la Collection) ---")
                        if iid:self.tree.set(iid,"state",f"BLOQUÉ — {len(missing)} morceau(x) absent(s) Collection")
                        continue

                    counts=parse_change_counts(pout)
                    self.append(f"\n--- Synchronisation : {pl} ---")
                    code,out=self.cmd(["apply",str(m3u),"--playlist",pl])
                    self.append(out)
                    if code==0:
                        synced+=1; adds+=counts["add"]; removes+=counts["remove"]
                        if iid:self.tree.set(iid,"state",f"Synchronisé • +{counts['add']} / -{counts['remove']}")
                    else:
                        failures+=1
                        if iid:self.tree.set(iid,"state",f"Bloqué/erreur — code {code}")

                summary=(f"{synced} playlist(s) synchronisée(s) • {len(missing_playlists)} créée(s) • "
                         f"+{adds} / -{removes} morceau(x) • {failures} erreur(s)/blocage(s)")
                self.append("\n=== RÉSUMÉ SYNCHRONISATION ===\n"+summary)
                self.status.set(summary)
                messagebox.showinfo(APP,"Synchronisation multi-playlists terminée.\n\n"+summary+
                                    "\n\nTu peux maintenant ouvrir Rekordbox.")
            except Exception as e:
                self.append("ERREUR: "+str(e)); messagebox.showerror(APP,str(e))
        threading.Thread(target=job,daemon=True).start()

    def install(self):
        if find_rbsync():
            self.doctor()
            return
        if not messagebox.askyesno(APP,
            "Installer rbsync dans un environnement isolé Python 3.13 ?\n"
            "Connexion Internet nécessaire. Aucune bibliothèque musicale ne sera modifiée.\n\nContinuer ?"):
            return
        self.status.set("Installation rbsync en cours…")
        def job():
            from datetime import datetime
            base=Path(os.getenv("LOCALAPPDATA", ""))/"rbsync"
            logs=base/"logs"
            logs.mkdir(parents=True,exist_ok=True)
            log=logs/("installation_lbr_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".log")
            py=base/"venv313"/"Scripts"/"python.exe"
            try:
                if not py.is_file():
                    raise RuntimeError("Python 3.13 isolé introuvable. Crée d'abord le venv313 avec : py -3.13 -m venv %LOCALAPPDATA%\\rbsync\\venv313")
                source="https://github.com/YasiSaps/rekordbox-playlist-sync/archive/main.zip"
                commands=([str(py),"-m","pip","install","--upgrade",source],
                          [str(py),"-m","rbsync","--help"])
                with log.open("w",encoding="utf-8") as fh:
                    for command in commands:
                        fh.write("Commande : "+" ".join(command)+"\n");fh.flush()
                        cp=run_process(command,stdout=fh,stderr=subprocess.STDOUT,timeout=300)
                        fh.write("Code retour : "+str(cp.returncode)+"\n");fh.flush()
                        if cp.returncode:
                            raise RuntimeError("Échec de l'installation ou de la vérification (code "+str(cp.returncode)+")")
                self.status.set("Installation rbsync terminée.")
                self.after(0,lambda:messagebox.showinfo(APP,"rbsync installé et vérifié.\nJournal : "+str(log)))
            except Exception as exc:
                detail=str(exc)
                self.status.set("Installation rbsync échouée.")
                self.after(0,lambda:messagebox.showerror(APP,detail+"\n\nJournal : "+str(log)))
        threading.Thread(target=job,daemon=True).start()

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from LBR_DJ_Library_Manager_FINAL import LBRManager
    LBRManager().mainloop()
