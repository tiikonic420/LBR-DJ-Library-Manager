import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from mutagen import File
from mutagen.id3 import ID3, ID3NoHeaderError, TCON, TDRC
from mutagen.mp4 import MP4
from mutagen.wave import WAVE
from mutagen.aiff import AIFF

APP_NAME = "Music Genre by LBR — FINAL V2"
SUPPORTED = {".mp3", ".flac", ".m4a", ".mp4", ".aac", ".ogg", ".opus", ".wav", ".aiff", ".aif"}

def detect_year(name):
    y = re.findall(r'(?<!\d)((?:19|20)\d{2})(?!\d)', name)
    return y[-1] if y else ""

def clean_genre(name):
    s = re.sub(r'(?<!\d)(?:19|20)\d{2}(?!\d)', '', name)
    s = re.sub(r'[\s_\-–—]+$', '', s)
    s = re.sub(r'^[\s_\-–—]+', '', s)
    s = re.sub(r'\s{2,}', ' ', s).strip()
    return s.upper()

def first(v):
    if v is None: return ""
    if isinstance(v, (list, tuple)): return str(v[0]) if v else ""
    return str(v)

def read_tags(path):
    genre = year = ""
    try:
        a = File(path, easy=True)
        if a is not None and a.tags:
            genre = first(a.tags.get("genre"))
            year = first(a.tags.get("date") or a.tags.get("year"))
            if isinstance(a.tags, ID3):
                genre = first(getattr(a.tags.get("TCON"), 'text', None)) or genre
                year = first(getattr(a.tags.get("TDRC"), 'text', None)) or year
        if Path(path).suffix.lower() in {".m4a", ".mp4", ".aac"}:
            m = MP4(path)
            if m.tags:
                genre = first(m.tags.get("\xa9gen")) or genre
                year = first(m.tags.get("\xa9day")) or year
    except Exception:
        pass
    ym = re.search(r'(?:19|20)\d{2}', year)
    return genre, ym.group(0) if ym else year

def write_tags(path, genre, year):
    ext = Path(path).suffix.lower()
    if ext in {'.wav', '.aiff', '.aif'}:
        audio = WAVE(path) if ext == '.wav' else AIFF(path)
        if audio.tags is None:audio.add_tags()
        audio.tags.setall('TCON', [TCON(encoding=3, text=[genre])])
        audio.tags.setall('TDRC', [TDRC(encoding=3, text=[year])])
        audio.save();return
    if ext == ".mp3":
        try: tags = ID3(path)
        except ID3NoHeaderError: tags = ID3()
        tags.delall("TCON"); tags.add(TCON(encoding=3, text=[genre]))
        tags.delall("TDRC"); tags.add(TDRC(encoding=3, text=[year]))
        tags.save(path); return
    if ext in {".m4a", ".mp4", ".aac"}:
        a = MP4(path)
        if a.tags is None: a.add_tags()
        a.tags["\xa9gen"] = [genre]; a.tags["\xa9day"] = [year]
        a.save(); return
    a = File(path, easy=True)
    if a is None: raise ValueError("Format non reconnu")
    if a.tags is None:
        try: a.add_tags()
        except Exception: pass
    a["genre"] = [genre]
    try: a["date"] = [year]
    except Exception: a["year"] = [year]
    a.save()

class App(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.folder = ""
        self.mode = None
        self.rows = []
        self.make_ui()

    def make_ui(self):
        from integrated_ui import build_genre
        build_genre(self)

    def clear(self):
        self.rows=[]
        children=self.tree.get_children()
        if children:self.tree.delete(*children)

    def logmsg(self,s):
        self.log.insert("end",s+"\n"); self.log.see("end"); self.update_idletasks()

    def choose_single(self):
        d=filedialog.askdirectory(title="Choisir le dossier à modifier")
        if not d:return
        self.folder=d; self.mode="single"; self.path.set(d)
        name=Path(d).name
        self.genre.set(clean_genre(name)); self.year.set(detect_year(name))
        self.genre_entry.config(state="normal")
        self.mode_label.set("Mode : DOSSIER UNIQUE — Genre et année modifiables")
        self.clear()
        self.status.set("Prêt pour l'analyse.")
        self.logmsg(f"DOSSIER UNIQUE : {d}")
        self.logmsg(f"Détecté → Genre={self.genre.get() or '(vide)'} | Année={self.year.get() or '(vide)'}")

    def choose_music(self):
        d=filedialog.askdirectory(title="Choisir le dossier MUSIC xxxx")
        if not d:return
        self.folder=d; self.mode="music"; self.path.set(d)
        self.genre.set("AUTOMATIQUE PAR SOUS-DOSSIER")
        self.year.set(detect_year(Path(d).name))
        self.genre_entry.config(state="disabled")
        self.mode_label.set("Mode : MUSIC xxxx — Genre automatique par premier sous-dossier")
        self.clear()
        self.status.set("Prêt pour l'analyse.")
        self.logmsg(f"MUSIC xxxx : {d}")
        self.logmsg(f"Année détectée → {self.year.get() or '(vide)'}")

    def validate(self):
        if not self.folder or not self.mode:
            messagebox.showwarning(APP_NAME,"Choisis d'abord un dossier."); return False
        y=self.year.get().strip()
        if not re.fullmatch(r"\d{4}",y):
            messagebox.showwarning(APP_NAME,"Corrige l'année : 4 chiffres sont nécessaires (ex. 2026)."); return False
        if self.mode=="single":
            g=self.genre.get().strip().upper(); self.genre.set(g)
            if not g:
                messagebox.showwarning(APP_NAME,"Corrige le genre."); return False
        return True

    def targets(self):
        out=[]
        if self.mode=="single":
            g=self.genre.get().strip().upper(); y=self.year.get().strip()
            for base,_,names in os.walk(self.folder):
                for n in names:
                    p=os.path.join(base,n)
                    if Path(n).suffix.lower() in SUPPORTED: out.append((p,g,y))
        else:
            y=self.year.get().strip()
            # Le premier dossier sous MUSIC xxxx détermine le genre, même si le fichier est plus profond.
            for child in sorted(Path(self.folder).iterdir(),key=lambda x:x.name.lower()):
                if not child.is_dir(): continue
                g=clean_genre(child.name)
                if not g: continue
                for base,_,names in os.walk(child):
                    for n in names:
                        p=os.path.join(base,n)
                        if Path(n).suffix.lower() in SUPPORTED: out.append((p,g,y))
        return sorted(out,key=lambda x:x[0].lower())

    def scan(self):
        if not self.validate(): return
        self.clear()
        self.status.set("Analyse en cours…"); self.update_idletasks()
        try:
            tg=self.targets()
            self.logmsg(f"Analyse : {len(tg)} fichier(s) audio détecté(s).")
            for p,g,y in tg:
                og,oy=read_tags(p)
                state="À modifier" if (og!=g or oy!=y) else "Déjà correct"
                row=(p,og,g,oy,y,state)
                self.rows.append(row)
                self.tree.insert("", "end", values=(os.path.relpath(p,self.folder),og,g,oy,y,state))
            todo=sum(r[5]=="À modifier" for r in self.rows)
            self.status.set(f"{len(self.rows)} morceau(x) • {todo} à modifier")
            if not self.rows:
                self.logmsg("Aucun fichier compatible trouvé. Vérifie le dossier et les extensions.")
                messagebox.showinfo(APP_NAME,"Aucun morceau compatible n'a été trouvé dans ce dossier.")
        except Exception as e:
            self.status.set("Erreur pendant l'analyse.")
            self.logmsg("ERREUR ANALYSE : "+repr(e))
            messagebox.showerror(APP_NAME,f"L'analyse a rencontré une erreur :\n\n{e}")

    def apply(self):
        if not self.validate(): return
        if not self.rows:
            messagebox.showwarning(APP_NAME,"Clique d'abord sur Analyser / Aperçu."); return
        # Empêche une correction manuelle après aperçu sans réanalyse.
        current=self.targets()
        expected={(p,g,y) for p,g,y in current}
        preview={(r[0],r[2],r[4]) for r in self.rows}
        if expected != preview:
            messagebox.showinfo(APP_NAME,"Le genre, l'année ou le contenu du dossier a changé.\nRelance Analyser / Aperçu avant d'appliquer.")
            return
        todo=[r for r in self.rows if r[5]=="À modifier"]
        if not todo:
            messagebox.showinfo(APP_NAME,"Tout est déjà correct."); return
        if not messagebox.askyesno(APP_NAME,f"Appliquer les changements à {len(todo)} fichier(s) ?\n\nSeuls Genre et Année seront modifiés."):
            return
        ok=0; errs=[]
        self.status.set("Modification en cours…"); self.update_idletasks()
        for r in todo:
            try:
                write_tags(r[0],r[2],r[4]); ok+=1
            except Exception as e: errs.append((r[0],str(e)))
        self.logmsg(f"Terminé : {ok} modifié(s), {len(errs)} erreur(s).")
        for p,e in errs[:30]: self.logmsg(f"ERREUR : {os.path.relpath(p,self.folder)} → {e}")
        if errs: messagebox.showwarning(APP_NAME,f"{ok} fichier(s) modifié(s), {len(errs)} erreur(s).\nConsulte le journal.")
        else: messagebox.showinfo(APP_NAME,f"{ok} fichier(s) modifié(s) avec succès.")
        self.scan()

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from LBR_DJ_Library_Manager_FINAL import LBRManager
    LBRManager().mainloop()
