import os
import re
import struct
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from urllib.parse import urlparse, unquote
import xml.etree.ElementTree as ET
from datetime import datetime
import json
import time
import base64
import hashlib

CONFIG_FILE = Path.home() / ".rekordbox_serato_sync_lbr.json"
HOTCUE_STATE_FILE = Path.home() / ".rekordbox_serato_hotcue_state_lbr.json"
SYNC_HISTORY_FILE = Path.home() / ".rekordbox_serato_sync_history_lbr.json"

APP_TITLE = "Rekordbox → Serato Sync by LBR - V1.4 FINAL 3"
VERSION_TEXT = "V1.4 FINAL 3 • Rekordbox → Serato • By LBR"

# ------------------------- FORMAT / PATH HELPERS -------------------------

def decode_location(value):
    if not value:
        return None
    value = unquote(value)
    if value.lower().startswith("file://"):
        parsed = urlparse(value)
        path = parsed.path
        if re.match(r"^/[A-Za-z]:/", path):
            path = path[1:]
        return path.replace("/", os.sep)
    return value

def sanitize_name(name):
    name = re.sub(r'[<>:"/\\|?*]', "_", name).strip().rstrip(".")
    return name or "Sans nom"

def tag(tagname, payload):
    return tagname.encode("ascii") + struct.pack(">I", len(payload)) + payload

def text_tag(tagname, text):
    return tag(tagname, text.encode("utf-16-be"))

def normalize_serato_path(p):
    """
    Chemin interne d'un .crate Serato sur Windows.
    Serato stocke le chemin relatif à la racine du volume qui contient _Serato_.
    Exemple G:\\MUSIQUE\\Titre.mp3 -> MUSIQUE/MUSIC 2026/Titre.mp3
    """
    s = str(p).replace("\\", "/").strip()
    if s.lower().startswith("file://"):
        s = decode_location(s).replace("\\", "/")
    s = unquote(s).lstrip("/")
    if re.match(r"^[A-Za-z]:/", s):
        s = s[3:]   # retire "G:/"
    return s.lstrip("/")


def make_crate(track_paths):
    """
    Génère la même structure de base qu'un .crate créé nativement par Serato DJ Pro.
    Le précédent moteur écrivait seulement vrsn + otrk/ptrk.
    Serato crée aussi les définitions de colonnes ovct avant les morceaux.
    """
    out = bytearray()
    out += text_tag("vrsn", "1.0/Serato ScratchLive Crate")

    # Structure observée dans un crate créé directement par Serato DJ Pro.
    columns = [
        ("song", "250"),
        ("artist", "250"),
        ("bpm", "30"),
        ("key", "30"),
        ("album", "250"),
        ("length", "250"),
        ("comment", "250"),
    ]
    for name, width in columns:
        payload = text_tag("tvcn", name) + text_tag("tvcw", width)
        out += tag("ovct", payload)

    for p in track_paths:
        nested = text_tag("ptrk", normalize_serato_path(p))
        out += tag("otrk", nested)
    return bytes(out)

def read_tlvs(data, start=0, end=None):
    if end is None:
        end = len(data)
    pos = start
    while pos + 8 <= end:
        try:
            name = data[pos:pos+4].decode("ascii")
        except Exception:
            break
        size = struct.unpack(">I", data[pos+4:pos+8])[0]
        p0, p1 = pos + 8, pos + 8 + size
        if p1 > end:
            break
        yield name, data[p0:p1]
        pos = p1

def read_crate_paths(crate_path):
    paths = []
    try:
        data = Path(crate_path).read_bytes()
        for name, payload in read_tlvs(data):
            if name == "otrk":
                for subname, subpayload in read_tlvs(payload):
                    if subname == "ptrk":
                        try:
                            paths.append(subpayload.decode("utf-16-be"))
                        except Exception:
                            pass
    except Exception:
        pass
    return paths

# ------------------------- REKORDBOX MODEL -------------------------

class Node:
    def __init__(self, name, node_type="folder", hierarchy=None, tracks=None):
        self.name = name
        self.node_type = node_type
        self.hierarchy = hierarchy or [name]
        self.tracks = tracks or []
        self.children = []

    @property
    def crate_name(self):
        return "%%".join(sanitize_name(x) for x in self.hierarchy)

    @property
    def display_path(self):
        return " > ".join(self.hierarchy)

def parse_rekordbox_xml(xml_path):
    root = ET.parse(xml_path).getroot()
    collection = {}
    collection_by_location = {}

    col = root.find("COLLECTION")
    if col is None:
        raise ValueError("Section COLLECTION introuvable dans le XML.")

    for tr in col.findall("TRACK"):
        tid = tr.get("TrackID")
        loc_raw = tr.get("Location")
        loc = decode_location(loc_raw)
        if tid:
            collection[tid] = loc
        if loc_raw:
            collection_by_location[loc_raw] = loc
        if loc:
            collection_by_location[loc] = loc

    pls = root.find("PLAYLISTS")
    if pls is None:
        raise ValueError("Section PLAYLISTS introuvable dans le XML.")

    roots = []
    playlists = []

    def convert(xmlnode, parents):
        typ = xmlnode.get("Type")
        name = xmlnode.get("Name", "Sans nom")

        # Rekordbox ROOT is a technical container, not a visible Serato crate.
        hierarchy = parents if (name.upper() == "ROOT" and typ == "0") else parents + [name]

        if typ == "1":
            keytype = xmlnode.get("KeyType", "0")
            tracks = []
            for ref in xmlnode.findall("TRACK"):
                key = ref.get("Key")
                if keytype == "0":
                    path = collection.get(key)
                else:
                    path = collection_by_location.get(key) or decode_location(key)
                if path:
                    tracks.append(path)
            node = Node(name, "playlist", hierarchy, tracks)
            playlists.append(node)
            return node

        node = Node(name, "folder", hierarchy, [])
        for child in xmlnode.findall("NODE"):
            node.children.append(convert(child, hierarchy))
        return node

    for n in pls.findall("NODE"):
        converted = convert(n, [])
        # Flatten the technical ROOT container.
        if converted.name.upper() == "ROOT" and converted.node_type == "folder":
            roots.extend(converted.children)
        else:
            roots.append(converted)

    return roots, playlists, len(collection)

def default_serato_folder():
    home = Path.home()
    candidates = [
        home / "Music" / "_Serato_",
        home / "My Music" / "_Serato_",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


# ------------------------- HOT CUES SERATO (MP3) -------------------------

def cue_entry(index, seconds, rgb, name=""):
    ms = max(0, int(round(float(seconds) * 1000)))
    name_b = name.encode("utf-8") + b"\x00"
    body = (
        b"\x00" + bytes([index & 0xff]) +
        struct.pack(">I", ms) +
        b"\x00" + bytes(rgb) +
        b"\x00\x00" + name_b
    )
    return b"CUE\x00" + struct.pack(">I", len(body)) + body

def loop_entry(index, start, end, rgb=(39, 170, 225), name=""):
    start_ms = max(0, int(round(float(start) * 1000)))
    end_ms = max(start_ms, int(round(float(end) * 1000)))
    name_b = name.encode("utf-8") + b"\x00"
    body = (
        b"\x00" + bytes([index & 0xff]) +
        struct.pack(">I", start_ms) +
        struct.pack(">I", end_ms) +
        b"\xff\xff\xff\xff" +
        bytes([0, *rgb]) +
        b"\x00\x00" +
        name_b
    )
    return b"LOOP\x00" + struct.pack(">I", len(body)) + body

def markers2_blob(cues, loops=None):
    loops = loops or []
    decoded = bytearray(b"\x01\x01")
    for c in sorted(cues, key=lambda x: x["index"]):
        decoded += cue_entry(c["index"], c["seconds"], c["rgb"], c["name"])
    for lp in sorted(loops, key=lambda x: x["index"]):
        decoded += loop_entry(lp["index"], lp["start"], lp["end"], lp["rgb"], lp["name"])
    decoded += b"\x00"
    enc = base64.b64encode(bytes(decoded))
    wrapped = b"\n".join(enc[i:i+72] for i in range(0, len(enc), 72))
    raw = b"\x01\x01" + wrapped
    if len(raw) < 470:
        raw += b"\x00" * (470 - len(raw))
    return raw

def parse_markers_by_path(xml_path):
    root = ET.parse(xml_path).getroot()
    col = root.find("COLLECTION")
    if col is None:
        raise ValueError("COLLECTION introuvable dans le XML.")
    result = {}
    for tr in col.findall("TRACK"):
        path = decode_location(tr.get("Location"))
        if not path:
            continue
        cues, hot_loops, memory_loops = [], [], []
        for pm in tr.findall("POSITION_MARK"):
            typ = pm.get("Type", "0")
            try:
                num = int(pm.get("Num", "-1"))
                start = float(pm.get("Start", "0"))
                end = float(pm.get("End", pm.get("Start", "0")))
            except Exception:
                continue
            def cv(k):
                try:
                    return max(0, min(255, int(pm.get(k, "0"))))
                except Exception:
                    return 0
            rgb = (cv("Red"), cv("Green"), cv("Blue"))
            name = pm.get("Name", "")
            if typ == "0" and 0 <= num <= 7:
                cues.append({"index": num, "seconds": start, "name": name, "rgb": rgb})
            elif typ == "4":
                marker = {
                    "start": start, "end": end, "name": name,
                    "rgb": rgb if any(rgb) else (39, 170, 225)
                }
                if 0 <= num <= 7:
                    marker["index"] = num
                    hot_loops.append(marker)
                else:
                    memory_loops.append(marker)

        used = {x["index"] for x in hot_loops}
        free = [i for i in range(8) if i not in used]
        loops = list(hot_loops)
        for i, ml in enumerate(sorted(memory_loops, key=lambda x: x["start"])):
            if i >= len(free):
                break
            loops.append({
                "index": free[i],
                "start": ml["start"],
                "end": ml["end"],
                "name": ml["name"] or f"Memory Loop {i+1}",
                "rgb": ml["rgb"],
            })
        if cues or loops:
            result[os.path.normcase(os.path.abspath(path))] = {"cues": cues, "loops": loops}
    return result

def parse_hot_cues_by_path(xml_path):
    # Compatibilité interne avec l'ancien moteur.
    return {k: v["cues"] for k, v in parse_markers_by_path(xml_path).items() if v["cues"]}

def inject_markers2_mp3(mp3_path, cues, loops=None):
    try:
        from mutagen.id3 import ID3, ID3NoHeaderError, GEOB
    except ImportError:
        raise RuntimeError("Le module Mutagen est requis pour les marqueurs MP3.")
    try:
        tags = ID3(mp3_path)
    except ID3NoHeaderError:
        tags = ID3()

    keep = [f for f in tags.getall("GEOB") if getattr(f, "desc", "") != "Serato Markers2"]
    tags.delall("GEOB")
    for f in keep:
        tags.add(f)
    tags.add(GEOB(
        encoding=0,
        mime="application/octet-stream",
        filename="",
        desc="Serato Markers2",
        data=markers2_blob(cues, loops or [])
    ))
    tags.save(mp3_path, v2_version=4)


def _serato_records_blob(cues, loops, extra_records=None):
    """Construit le contenu Markers2 interne. extra_records préserve COLOR/BPMLOCK FLAC."""
    decoded = bytearray(b"\x01\x01")
    extra_records = extra_records or []
    for typ, body in extra_records:
        if typ == b"COLOR":
            decoded += typ + b"\x00" + struct.pack(">I", len(body)) + body
    for c in sorted(cues, key=lambda x: x["index"]):
        decoded += cue_entry(c["index"], c["seconds"], c["rgb"], c["name"])
    for lp in sorted(loops, key=lambda x: x["index"]):
        decoded += loop_entry(lp["index"], lp["start"], lp["end"], lp["rgb"], lp["name"])
    for typ, body in extra_records:
        if typ != b"COLOR":
            decoded += typ + b"\x00" + struct.pack(">I", len(body)) + body
    return bytes(decoded)

def inject_markers2_aiff(aiff_path, cues, loops=None):
    try:
        from mutagen.aiff import AIFF
        from mutagen.id3 import GEOB
    except ImportError:
        raise RuntimeError("Mutagen est requis pour les marqueurs AIFF.")
    audio = AIFF(aiff_path)
    if audio.tags is None:
        audio.add_tags()

    keep = [f for f in audio.tags.getall("GEOB") if getattr(f, "desc", "") != "Serato Markers2"]
    audio.tags.delall("GEOB")
    for f in keep:
        audio.tags.add(f)
    audio.tags.add(GEOB(
        encoding=0,
        mime="application/octet-stream",
        filename="",
        desc="Serato Markers2",
        data=markers2_blob(cues, loops or [])
    ))
    audio.save()

def _parse_serato_inner_records(inner):
    records = []
    pos = 2
    while pos < len(inner):
        z = inner.find(b"\x00", pos)
        if z < 0 or z + 5 > len(inner):
            break
        typ = inner[pos:z]
        if not typ:
            break
        ln = struct.unpack(">I", inner[z+1:z+5])[0]
        end = z + 5 + ln
        if end > len(inner):
            break
        records.append((typ, inner[z+5:end]))
        pos = end
    return records

def inject_markers2_flac(flac_path, cues, loops=None):
    """
    FLAC V1.4: conserve l'enveloppe créée par Serato et les records auxiliaires
    COLOR/BPMLOCK. Un FLAC sans SERATO_MARKERS_V2 n'est pas modifié par sécurité.
    """
    try:
        from mutagen.flac import FLAC
    except ImportError:
        raise RuntimeError("Mutagen est requis pour les marqueurs FLAC.")

    audio = FLAC(flac_path)
    vals = audio.get("serato_markers_v2") or audio.get("SERATO_MARKERS_V2")
    if not vals:
        raise RuntimeError(
            "FLAC non initialisé par Serato : charge/analyse d'abord ce morceau dans Serato."
        )

    try:
        raw = base64.b64decode(vals[0])
    except Exception as e:
        raise RuntimeError(f"SERATO_MARKERS_V2 illisible : {e}")

    prefix = b"application/octet-stream\x00\x00Serato Markers2\x00"
    if not raw.startswith(prefix):
        raise RuntimeError("Structure SERATO_MARKERS_V2 non reconnue.")

    payload = raw[len(prefix):]
    if not payload.startswith(b"\x01\x01"):
        raise RuntimeError("Payload Markers2 FLAC non reconnu.")

    inner_text = payload[2:].rstrip(b"\x00").replace(b"\n", b"")
    try:
        inner = base64.b64decode(inner_text)
    except Exception as e:
        raise RuntimeError(f"Payload Markers2 FLAC invalide : {e}")

    existing = _parse_serato_inner_records(inner)
    extras = [(t, b) for t, b in existing if t not in (b"CUE", b"LOOP")]

    rebuilt = _serato_records_blob(cues, loops or [], extras)
    inner64 = base64.b64encode(rebuilt)
    wrapped = b"\n".join(inner64[i:i+72] for i in range(0, len(inner64), 72))
    new_payload = b"\x01\x01" + wrapped
    new_raw = prefix + new_payload

    # La structure Serato testée utilisait un conteneur fixe. Ne jamais le dépasser.
    if len(new_raw) > len(raw):
        raise RuntimeError(
            "Les marqueurs dépassent la taille du conteneur Serato FLAC existant."
        )
    new_raw = new_raw.ljust(len(raw), b"\x00")

    outer = base64.b64encode(new_raw)
    outer_wrapped = b"\n".join(outer[i:i+72] for i in range(0, len(outer), 72)).decode("ascii") + "\n"
    audio["SERATO_MARKERS_V2"] = [outer_wrapped]
    audio.save()

def inject_serato_markers(audio_path, cues, loops=None):
    ext = Path(audio_path).suffix.lower()
    if ext == ".mp3":
        inject_markers2_mp3(audio_path, cues, loops or [])
    elif ext in (".aif", ".aiff"):
        inject_markers2_aiff(audio_path, cues, loops or [])
    elif ext == ".flac":
        inject_markers2_flac(audio_path, cues, loops or [])
    else:
        raise RuntimeError(f"Format non pris en charge pour les marqueurs : {ext}")


def find_serato_roots():
    """Détecte les dossiers _Serato_ présents à la racine des volumes Windows."""
    roots = []
    if os.name == "nt":
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            root = Path(f"{letter}:\\")
            try:
                candidate = root / "_Serato_"
                if candidate.is_dir():
                    roots.append(candidate)
            except Exception:
                pass
    return roots



def hotcue_signature(cues, loops=None):
    clean = {"cues": [], "loops": []}
    for c in sorted(cues, key=lambda x: x["index"]):
        clean["cues"].append({
            "index": int(c["index"]),
            "ms": round(float(c["seconds"]) * 1000),
            "name": c.get("name", ""),
            "rgb": list(c.get("rgb", (0, 0, 0))),
        })
    for lp in sorted(loops or [], key=lambda x: x["index"]):
        clean["loops"].append({
            "index": int(lp["index"]),
            "start_ms": round(float(lp["start"]) * 1000),
            "end_ms": round(float(lp["end"]) * 1000),
            "name": lp.get("name", ""),
            "rgb": list(lp.get("rgb", (39, 170, 225))),
        })
    raw = json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
def load_hotcue_state():
    try:
        if HOTCUE_STATE_FILE.exists():
            data = json.loads(HOTCUE_STATE_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}

def save_hotcue_state(state):
    HOTCUE_STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8"
    )


# ------------------------- GUI -------------------------

class App(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.xml_path = tk.StringVar()
        self.serato_path = tk.StringVar(value=str(default_serato_folder()))
        self.status = tk.StringVar(value="Sélectionne un export XML Rekordbox.")
        self.auto_watch = tk.BooleanVar(value=True)
        self.last_xml_mtime = None
        self.xml_changed = False
        self.summary = tk.StringVar(value="Aucune analyse")
        self.source_state = tk.StringVar(value="XML : —")
        self.serato_state = tk.StringVar(value="Serato : —")
        self.detected_serato_roots = []
        self.playlist_filter = tk.StringVar()
        self.playlist_filter.trace_add("write", lambda *_: self.apply_playlist_filter())

        self.roots = []
        self.playlists = []
        self.item_to_node = {}
        self.checked = set()

        self.load_settings()
        self.build()
        self.after(1000, self.startup_load)
        self.after(2500, self.watch_xml)

    def load_settings(self):
        try:
            if CONFIG_FILE.exists():
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                self.xml_path.set(data.get("xml_path", ""))
                self.serato_path.set(data.get("serato_path", str(default_serato_folder())))
                self.auto_watch.set(bool(data.get("auto_watch", True)))
        except Exception:
            pass

    def save_settings(self):
        try:
            CONFIG_FILE.write_text(json.dumps({
                "xml_path": self.xml_path.get(),
                "serato_path": self.serato_path.get(),
                "auto_watch": self.auto_watch.get()
            }, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def startup_load(self):
        self.auto_detect_serato(silent=True)
        p = Path(self.xml_path.get()) if self.xml_path.get() else None
        if p and p.exists():
            self.load_xml()

    def xml_mtime(self):
        try:
            return Path(self.xml_path.get()).stat().st_mtime
        except Exception:
            return None

    def watch_xml(self):
        try:
            if self.auto_watch.get() and self.xml_path.get():
                mt = self.xml_mtime()
                if mt is not None:
                    if self.last_xml_mtime is None:
                        self.last_xml_mtime = mt
                    elif mt != self.last_xml_mtime:
                        self.last_xml_mtime = mt
                        self.xml_changed = True
                        self.status.set("Nouveau XML Rekordbox détecté • clique ACTUALISER.")
                        self.source_state.set("XML : MODIFIÉ • actualisation requise")
                        self.refresh_btn.configure(text="ACTUALISER • NOUVEAU XML")
        finally:
            self.after(2500, self.watch_xml)

    def reload_xml(self):
        if not self.xml_path.get() or not Path(self.xml_path.get()).exists():
            messagebox.showwarning("XML Rekordbox", "Le fichier XML configuré est introuvable.")
            return
        self.load_xml()
        self.xml_changed = False
        self.refresh_btn.configure(text="ACTUALISER")
        self.last_xml_mtime = self.xml_mtime()

    def build(self):
        from integrated_ui import build_serato
        build_serato(self)

    def write_log(self, msg, clear=False):
        self.log.configure(state="normal")
        if clear:
            self.log.delete("1.0", "end")
        self.log.insert("end", msg.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def choose_xml(self):
        f = filedialog.askopenfilename(
            title="Export XML Rekordbox",
            filetypes=[("Rekordbox XML","*.xml"),("Tous les fichiers","*.*")]
        )
        if f:
            self.xml_path.set(f)
            self.save_settings()
            self.load_xml()
            self.last_xml_mtime = self.xml_mtime()

    def auto_detect_serato(self, silent=False):
        roots = find_serato_roots()
        self.detected_serato_roots = roots

        if not roots:
            self.serato_state.set("Serato : _Serato_ non détecté")
            if not silent:
                messagebox.showinfo("Détection Serato", "Aucun dossier _Serato_ détecté à la racine des disques.")
            return

        current = Path(self.serato_path.get()) if self.serato_path.get() else None

        # Prefer a detected root on the same volume as the XML/audio library when possible.
        chosen = None
        try:
            xml_drive = Path(self.xml_path.get()).drive.upper() if self.xml_path.get() else ""
            same = [r for r in roots if r.drive.upper() == xml_drive]
            if same:
                chosen = same[0]
        except Exception:
            pass

        # Otherwise preserve a currently valid detected root.
        if chosen is None and current:
            for r in roots:
                try:
                    if r.resolve() == current.resolve():
                        chosen = r
                        break
                except Exception:
                    pass

        # If there is only one _Serato_, it is unambiguous.
        if chosen is None and len(roots) == 1:
            chosen = roots[0]

        # If several exist, prefer the one whose volume contains the most XML tracks.
        if chosen is None and self.xml_path.get() and Path(self.xml_path.get()).exists():
            try:
                root = ET.parse(self.xml_path.get()).getroot()
                col = root.find("COLLECTION")
                counts = {r.drive.upper(): 0 for r in roots}
                if col is not None:
                    for tr in col.findall("TRACK"):
                        p = decode_location(tr.get("Location"))
                        d = Path(p).drive.upper() if p else ""
                        if d in counts:
                            counts[d] += 1
                chosen = max(roots, key=lambda r: counts.get(r.drive.upper(), 0))
            except Exception:
                pass

        if chosen is None:
            chosen = roots[0]

        self.serato_path.set(str(chosen))
        self.save_settings()
        self.serato_state.set(f"Serato : AUTO • {chosen}")
        if not silent:
            others = [str(r) for r in roots if r != chosen]
            msg = f"Dossier Serato sélectionné automatiquement :\n{chosen}"
            if others:
                msg += "\n\nAutre(s) dossier(s) détecté(s) :\n" + "\n".join(others)
            messagebox.showinfo("Détection Serato", msg)

    def choose_serato(self):
        d = filedialog.askdirectory(title="Sélectionne le dossier _Serato_")
        if d:
            self.serato_path.set(d)
            self.save_settings()
            self.refresh_statuses()

    def load_xml(self):
        try:
            self.roots, self.playlists, count = parse_rekordbox_xml(self.xml_path.get())
            self.item_to_node.clear()
            self.checked.clear()
            for item in self.tree.get_children():
                self.tree.delete(item)

            def insert(node, parent=""):
                item = self.tree.insert(
                    parent, "end",
                    text="☑ " + node.name,
                    values=(len(node.tracks) if node.node_type=="playlist" else "", "")
                )
                self.item_to_node[item] = node
                self.checked.add(item)
                for ch in node.children:
                    insert(ch, item)
                self.tree.item(item, open=True)

            for root in self.roots:
                insert(root)

            self.status.set(f"{count} morceaux dans COLLECTION • {len(self.playlists)} playlists détectées.")
            self.source_state.set(f"XML : OK • {Path(self.xml_path.get()).name}")
            self.serato_state.set("Serato : OK" if Path(self.serato_path.get()).exists() else "Serato : dossier à vérifier")
            self.write_log(
                f"=== XML REKORDBOX ===\n"
                f"Collection : {count} morceaux\n"
                f"Playlists : {len(self.playlists)}\n", clear=True
            )
            self.last_xml_mtime = self.xml_mtime()
            self.xml_changed = False
            if hasattr(self, "refresh_btn"):
                self.refresh_btn.configure(text="ACTUALISER")
            self.save_settings()
            self.refresh_statuses()
        except Exception as e:
            messagebox.showerror("Erreur XML", str(e))

    def descendants(self, item):
        result = [item]
        for c in self.tree.get_children(item):
            result.extend(self.descendants(c))
        return result

    def set_checked(self, item, value):
        targets = self.descendants(item)
        for x in targets:
            if value:
                self.checked.add(x)
            else:
                self.checked.discard(x)
            node = self.item_to_node.get(x)
            if node:
                self.tree.item(x, text=("☑ " if x in self.checked else "☐ ") + node.name)

    def set_all(self, value):
        for item in self.tree.get_children():
            self.set_checked(item, value)

    def on_tree_click(self, event):
        item = self.tree.identify_row(event.y)
        region = self.tree.identify("region", event.x, event.y)
        if not item or region != "tree":
            return
        # Only toggle if click is near the checkbox/text area.
        bbox = self.tree.bbox(item, "#0")
        if bbox and event.x <= bbox[0] + 35:
            self.set_checked(item, item not in self.checked)
            return "break"

    def apply_playlist_filter(self):
        """Filtre visuel uniquement : ne modifie ni les playlists ni les crates."""
        if not hasattr(self, "tree"):
            return
        q = self.playlist_filter.get().strip().lower()
        # Rebuild the tree to keep hierarchy understandable.
        saved_nodes = {id(node) for item,node in self.item_to_node.items() if item in self.checked}
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.item_to_node.clear()
        self.checked.clear()

        def matches(node):
            if not q:
                return True
            if q in node.display_path.lower():
                return True
            return any(matches(ch) for ch in node.children)

        def insert(node, parent=""):
            if not matches(node):
                return
            item = self.tree.insert(
                parent, "end",
                text=("☑ " if id(node) in saved_nodes else "☐ ") + node.name,
                values=(len(node.tracks) if node.node_type=="playlist" else "", "")
            )
            self.item_to_node[item] = node
            if id(node) in saved_nodes:
                self.checked.add(item)
            for ch in node.children:
                insert(ch, item)
            self.tree.item(item, open=True)

        for root in self.roots:
            insert(root)
        self.refresh_statuses()

    def select_changed_only(self):
        """Coche uniquement les playlists dont la crate n'est pas IDENTIQUE."""
        self.checked.clear()
        changed = 0
        for item,node in self.item_to_node.items():
            if node.node_type == "playlist":
                st,_,_ = self.compare_playlist(node)
                if st != "IDENTIQUE":
                    self.checked.add(item)
                    changed += 1
        # Mark parent folders when at least one descendant is selected.
        for item,node in reversed(list(self.item_to_node.items())):
            if node.node_type != "playlist":
                if any(x in self.checked for x in self.descendants(item)[1:]):
                    self.checked.add(item)
        for item,node in self.item_to_node.items():
            self.tree.item(item, text=("☑ " if item in self.checked else "☐ ") + node.name)
        self.status.set(f"{changed} playlist(s) modifiée(s) sélectionnée(s).")

    def open_backups(self):
        folder = Path(self.serato_path.get()) / "LBR_Backups"
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(folder))
        except Exception:
            messagebox.showinfo("Sauvegardes", str(folder))

    def _load_history(self):
        try:
            if SYNC_HISTORY_FILE.exists():
                d=json.loads(SYNC_HISTORY_FILE.read_text(encoding="utf-8"))
                return d if isinstance(d,list) else []
        except Exception:
            pass
        return []

    def _add_history(self, entry):
        hist=self._load_history()
        hist.insert(0,entry)
        hist=hist[:30]
        try:
            SYNC_HISTORY_FILE.write_text(json.dumps(hist,ensure_ascii=False,indent=2),encoding="utf-8")
        except Exception:
            pass

    def show_sync_history(self):
        hist=self._load_history()
        if not hist:
            messagebox.showinfo("Historique", "Aucune synchronisation enregistrée.")
            return
        lines=["=== HISTORIQUE DES SYNCHRONISATIONS ===",""]
        for h in hist[:15]:
            lines.append(
                f"{h.get('date','?')} • playlists {h.get('playlists',0)} • "
                f"+{h.get('added',0)}/-{h.get('removed',0)} • "
                f"Hot Cues {h.get('cues',0)} • Loops {h.get('loops',0)}"
            )
        self.write_log("\n".join(lines),clear=True)
        messagebox.showinfo("Historique", "\n".join(lines[:10]))

    def simulate_sync(self):
        """Analyse complète de SYNC AUTO sans aucune écriture."""
        selected=self.selected_playlists()
        if not selected:
            messagebox.showwarning("Simulation","Aucune playlist sélectionnée.")
            return
        created=updated=added=removed=0
        details=[]
        for pl in selected:
            st,a,r=self.compare_playlist(pl)
            if st=="IDENTIQUE":
                continue
            if st=="À CRÉER": created+=1
            else: updated+=1
            added+=a; removed+=r
            details.append(f"• {pl.display_path} : {st}")

        try:
            marker_map=parse_markers_by_path(self.xml_path.get())
            prev=load_hotcue_state()
            marker_files=cues_n=loops_n=ignored=missing=0
            seen=set()
            for pl in selected:
                for p in pl.tracks:
                    if not p: continue
                    k=os.path.normcase(os.path.abspath(p))
                    if k in seen: continue
                    seen.add(k)
                    m=marker_map.get(k,{"cues":[],"loops":[]})
                    sig=hotcue_signature(m["cues"],m["loops"])
                    old=prev.get(k)
                    changed=(old is None and bool(m["cues"] or m["loops"])) or (old is not None and old!=sig)
                    if not changed: continue
                    if not Path(p).exists(): missing+=1; continue
                    if Path(p).suffix.lower() not in (".mp3",".aif",".aiff",".flac"):
                        ignored+=1; continue
                    marker_files+=1; cues_n+=len(m["cues"]); loops_n+=len(m["loops"])
        except Exception as e:
            messagebox.showerror("Simulation",str(e)); return

        lines=[
            "=== MODE SIMULATION - AUCUNE ÉCRITURE ===","",
            f"Playlists à créer : {created}",f"Playlists à mettre à jour : {updated}",
            f"Titres à ajouter : {added}",f"Titres à retirer : {removed}","",
            f"Fichiers marqueurs à modifier : {marker_files}",
            f"Hot Cues à écrire : {cues_n}",f"Saved Loops à écrire : {loops_n}",
            f"Marqueurs ignorés : {ignored}",f"Fichiers introuvables : {missing}",""
        ]+details
        self.write_log("\n".join(lines),clear=True)
        messagebox.showinfo("Simulation terminée",
            f"Aucune modification effectuée.\n\nPlaylists : {created+updated}\n"
            f"Titres : +{added} / -{removed}\nHot Cues : {cues_n}\nSaved Loops : {loops_n}")

    def marker_preview(self):
        """Aperçu moderne des marqueurs MP3/AIFF/FLAC sélectionnés."""
        selected=self.selected_track_paths()
        if not selected:
            messagebox.showwarning("Marqueurs","Aucun titre sélectionné.")
            return
        try:
            marker_map=parse_markers_by_path(self.xml_path.get())
        except Exception as e:
            messagebox.showerror("Marqueurs",str(e)); return
        counts={".mp3":0,".aif":0,".aiff":0,".flac":0}
        files=cues=loops=unsupported=missing=0
        lines=["=== APERÇU MARQUEURS ==="]
        for p in selected:
            k=os.path.normcase(os.path.abspath(p))
            m=marker_map.get(k,{"cues":[],"loops":[]})
            if not (m["cues"] or m["loops"]): continue
            if not Path(p).exists(): missing+=1; continue
            ext=Path(p).suffix.lower()
            if ext not in counts: unsupported+=1; continue
            files+=1; counts[ext]+=1; cues+=len(m["cues"]); loops+=len(m["loops"])
            lines.append(f"{Path(p).name} : {len(m['cues'])} cue(s), {len(m['loops'])} loop(s)")
        lines[1:1]=[
            f"Fichiers avec marqueurs : {files}",
            f"MP3 : {counts['.mp3']} • AIFF/AIF : {counts['.aiff']+counts['.aif']} • FLAC : {counts['.flac']}",
            f"Hot Cues : {cues} • Saved Loops : {loops}",
            f"Formats ignorés : {unsupported} • Introuvables : {missing}",""
        ]
        self.write_log("\n".join(lines),clear=True)
        messagebox.showinfo("Marqueurs",
            f"Fichiers : {files}\nHot Cues : {cues}\nSaved Loops : {loops}\n"
            f"Formats ignorés : {unsupported}\nIntrouvables : {missing}")

    def selected_playlists(self):
        return [
            node for item,node in self.item_to_node.items()
            if item in self.checked and node.node_type == "playlist"
        ]

    def crate_path(self, pl):
        return Path(self.serato_path.get()) / "Subcrates" / f"{pl.crate_name}.crate"

    def compare_playlist(self, pl):
        cp = self.crate_path(pl)
        expected = [normalize_serato_path(p) for p in pl.tracks if p and Path(p).exists()]
        if not cp.exists():
            return "À CRÉER", len(expected), 0

        current = read_crate_paths(cp)
        # Compare as ordered lists; crate order matters to DJs.
        if current == expected:
            return "IDENTIQUE", 0, 0

        exp_set = set(expected)
        cur_set = set(current)
        added = len(exp_set - cur_set)
        removed = len(cur_set - exp_set)
        if added or removed:
            return f"+{added} / -{removed}", added, removed
        return "ORDRE MODIFIÉ", 0, 0

    def refresh_statuses(self):
        if not self.playlists:
            return
        total_add = total_remove = 0
        lines = ["=== COMPARAISON SERATO ==="]
        for item,node in self.item_to_node.items():
            if node.node_type != "playlist":
                continue
            status, add, rem = self.compare_playlist(node)
            vals = list(self.tree.item(item, "values"))
            self.tree.item(item, values=(len(node.tracks), status))
            total_add += add
            total_remove += rem
            lines.append(f"{node.display_path} : {status}")
        lines.append("")
        lines.append(f"À ajouter : {total_add}")
        lines.append(f"À retirer : {total_remove}")
        changed = 0
        identical = 0
        to_create = 0
        for node in self.playlists:
            st, _, _ = self.compare_playlist(node)
            if st == "IDENTIQUE":
                identical += 1
            else:
                changed += 1
                if st == "À CRÉER":
                    to_create += 1
        self.summary.set(f"{identical} identique(s) • {changed} changement(s) • {to_create} à créer")
        self.serato_state.set("Serato : OK" if Path(self.serato_path.get()).exists() else "Serato : dossier à vérifier")
        self.write_log("\n".join(lines), clear=True)

    def run_diagnostic(self, silent=False):
        """Contrôle les fichiers sélectionnés sans rien modifier.
        Les erreurs concernent l'utilisation dans les crates.
        Les avertissements concernent uniquement la synchro des marqueurs.
        """
        selected = self.selected_playlists()
        if not selected:
            if not silent:
                messagebox.showwarning("Diagnostic", "Aucune playlist sélectionnée.")
            return None

        serato_root = Path(self.serato_path.get()) if self.serato_path.get() else None
        serato_drive = serato_root.drive.upper() if serato_root else ""

        paths = {}
        for pl in selected:
            for p in pl.tracks:
                if p:
                    key = os.path.normcase(os.path.abspath(p))
                    paths[key] = (p, pl.display_path)

        ok_crate = []
        missing = []
        wrong_volume = []
        marker_unsupported = []
        flac_uninitialized = []

        marker_supported = {".mp3", ".aif", ".aiff", ".flac"}

        for _, (p, playlist_name) in paths.items():
            path = Path(p)
            item = (playlist_name, p)

            # Bloquant pour la crate : le fichier doit exister.
            if not path.exists():
                missing.append(item)
                continue

            # Bloquant avec le moteur de chemins relatif au volume Serato validé.
            if serato_drive and path.drive.upper() != serato_drive:
                wrong_volume.append(item)
                continue

            # À ce stade le fichier est utilisable dans une crate, WAV compris.
            ok_crate.append(item)

            ext = path.suffix.lower()

            # Non bloquant : le format reste utilisable dans la crate,
            # mais notre moteur de marqueurs ne l'écrit pas encore.
            if ext not in marker_supported:
                marker_unsupported.append(item)
                continue

            # Non bloquant pour la crate, mais bloque l'écriture de marqueurs FLAC.
            if ext == ".flac":
                try:
                    from mutagen.flac import FLAC
                    audio = FLAC(path)
                    vals = audio.get("serato_markers_v2") or audio.get("SERATO_MARKERS_V2")
                    if not vals:
                        flac_uninitialized.append(item)
                except Exception:
                    flac_uninitialized.append(item)

        errors = len(missing) + len(wrong_volume)
        warnings = len(marker_unsupported) + len(flac_uninitialized)

        lines = [
            "=== DIAGNOSTIC V1.4 ===",
            f"Playlists sélectionnées : {len(selected)}",
            f"Fichiers uniques : {len(paths)}",
            f"✅ Utilisables dans les crates : {len(ok_crate)}",
            f"❌ ERREURS bloquantes : {errors}",
            f"⚠ AVERTISSEMENTS marqueurs : {warnings}",
            "",
        ]

        def add_section(title, entries, reason):
            if not entries:
                return
            lines.append(f"--- {title} ({len(entries)}) ---")
            for playlist_name, p in entries:
                lines.append(f"[{playlist_name}] {Path(p).name}")
                lines.append(f"  {p}")
                lines.append(f"  -> {reason}")
            lines.append("")

        add_section(
            "ERREUR - FICHIERS INTROUVABLES",
            missing,
            "Le chemin indiqué dans le XML Rekordbox n'existe pas. Ce titre ne peut pas être ajouté à la crate."
        )
        add_section(
            "ERREUR - MAUVAIS VOLUME",
            wrong_volume,
            f"Le fichier n'est pas sur le volume Serato {serato_drive or '(non détecté)'}. "
            "Le moteur de chemins relatif validé ne peut pas l'ajouter correctement."
        )
        add_section(
            "AVERTISSEMENT - MARQUEURS NON PRIS EN CHARGE",
            marker_unsupported,
            "Le fichier reste utilisable dans la crate. Seule l'écriture Hot Cues/Saved Loops "
            "est ignorée. Marqueurs actuellement pris en charge : MP3, AIF/AIFF et FLAC."
        )
        add_section(
            "AVERTISSEMENT - FLAC NON INITIALISÉS PAR SERATO",
            flac_uninitialized,
            "Le fichier reste utilisable dans la crate, mais les Hot Cues/Saved Loops ne seront "
            "pas écrits tant que SERATO_MARKERS_V2 n'existe pas."
        )

        if errors == 0:
            lines.append("CRATES : aucun problème bloquant détecté.")
            if warnings:
                lines.append("SYNC AUTO peut être lancé ; les avertissements concernent uniquement les marqueurs.")
            else:
                lines.append("SYNC AUTO peut être lancé.")
        else:
            lines.append("Corrige les ERREURS bloquantes ci-dessus pour une synchronisation complète des crates.")

        lines.append("")
        lines.append("Aucune modification n'a été effectuée.")

        report = "\n".join(lines)
        self.write_log(report, clear=True)

        if not silent:
            if errors:
                messagebox.showwarning(
                    "Diagnostic terminé",
                    f"{errors} erreur(s) bloquante(s) pour les crates.\n"
                    f"{warnings} avertissement(s) pour les marqueurs.\n\n"
                    f"Fichiers introuvables : {len(missing)}\n"
                    f"Mauvais volume : {len(wrong_volume)}\n"
                    f"Formats sans écriture de marqueurs : {len(marker_unsupported)}\n"
                    f"FLAC non initialisés : {len(flac_uninitialized)}\n\n"
                    "Le détail est affiché dans le Journal."
                )
            elif warnings:
                messagebox.showinfo(
                    "Diagnostic terminé",
                    f"Aucune erreur bloquante pour les crates.\n"
                    f"{warnings} avertissement(s) concernent uniquement les marqueurs.\n\n"
                    "SYNC AUTO peut être lancé.\nLe détail est affiché dans le Journal."
                )
            else:
                messagebox.showinfo(
                    "Diagnostic terminé",
                    f"{len(paths)} fichier(s) contrôlé(s).\n"
                    "Aucune erreur ni avertissement.\n\nTu peux lancer SYNC AUTO."
                )

        return {
            "errors": errors,
            "warnings": warnings,
            "ok_crate": ok_crate,
            "missing": missing,
            "wrong_volume": wrong_volume,
            "marker_unsupported": marker_unsupported,
            "flac_uninitialized": flac_uninitialized,
        }

    def sync_changes(self):
        selected = self.selected_playlists()
        if not selected:
            messagebox.showwarning("Sélection", "Aucune playlist sélectionnée.")
            return

        changed_playlists = []
        for pl in selected:
            status, _, _ = self.compare_playlist(pl)
            if status != "IDENTIQUE":
                changed_playlists.append(pl)

        try:
            marker_map = parse_markers_by_path(self.xml_path.get())
        except Exception as e:
            messagebox.showerror("Marqueurs", f"Impossible d'analyser les Hot Cues / Loops :\n{e}")
            return

        previous_state = load_hotcue_state()
        next_state = dict(previous_state)

        selected_paths = {}
        for pl in selected:
            for p in pl.tracks:
                if p:
                    key = os.path.normcase(os.path.abspath(p))
                    selected_paths[key] = p

        marker_changed = []
        unsupported = 0
        missing = 0

        for key, original_path in selected_paths.items():
            markers = marker_map.get(key, {"cues": [], "loops": []})
            cues = markers["cues"]
            loops = markers["loops"]
            sig = hotcue_signature(cues, loops)
            old_sig = previous_state.get(key)

            changed = (old_sig is None and bool(cues or loops)) or (old_sig is not None and old_sig != sig)
            if not changed:
                continue
            if not Path(original_path).exists():
                missing += 1
                continue
            if Path(original_path).suffix.lower() not in (".mp3", ".aif", ".aiff", ".flac"):
                unsupported += 1
                continue
            marker_changed.append((original_path, cues, loops, sig))

        if not changed_playlists and not marker_changed:
            messagebox.showinfo(
                "Synchronisation",
                "Aucun changement de playlist, Hot Cue ou Loop à synchroniser."
            )
            return

        total_cues = sum(len(cues) for _, cues, _, _ in marker_changed)
        total_loops = sum(len(loops) for _, _, loops, _ in marker_changed)

        # V1.4 : aperçu détaillé avant toute écriture.
        created_count = 0
        updated_count = 0
        total_added = 0
        total_removed = 0
        playlist_details = []

        for pl in changed_playlists:
            status, added, removed = self.compare_playlist(pl)
            # compare_playlist() renvoie déjà les nombres ajoutés/retirés.
            add_count = int(added)
            remove_count = int(removed)
            total_added += add_count
            total_removed += remove_count
            if status == "À CRÉER":
                created_count += 1
                action = "CRÉER"
            else:
                updated_count += 1
                action = "METTRE À JOUR"
            playlist_details.append(
                f"• {pl.display_path} : {action}  (+{add_count} / -{remove_count})"
            )

        warning_count = unsupported + missing
        preview_lines = [
            "=== APERÇU AVANT SYNCHRONISATION ===",
            "",
            f"Playlists à créer : {created_count}",
            f"Playlists à mettre à jour : {updated_count}",
            f"Titres à ajouter : {total_added}",
            f"Titres à retirer : {total_removed}",
            "",
            f"Fichiers avec marqueurs modifiés : {len(marker_changed)}",
            f"Hot Cues à écrire : {total_cues}",
            f"Saved Loops à écrire : {total_loops}",
            "",
            f"Avertissements : {warning_count}",
        ]
        if unsupported:
            preview_lines.append(
                f"  • Marqueurs ignorés (hors MP3/AIFF/FLAC) : {unsupported}"
            )
        if missing:
            preview_lines.append(f"  • Fichiers introuvables : {missing}")

        if playlist_details:
            preview_lines += ["", "--- PLAYLISTS ---"] + playlist_details

        preview_lines += [
            "",
            "Sauvegarde automatique avant écriture.",
            "Serato doit être fermé.",
            "",
            "Lancer la synchronisation ?"
        ]
        msg = "\n".join(preview_lines)

        # Le même aperçu reste visible dans le journal après fermeture de la fenêtre.
        self.write_log("\n".join(preview_lines[:-1]), clear=True)

        if not messagebox.askyesno("APERÇU SYNC AUTO - V1.4", msg):
            self.write_log("\nSynchronisation annulée par l'utilisateur.")
            return

        original_checked = set(self.checked)
        try:
            if changed_playlists:
                changed_ids = {
                    item for item, node in self.item_to_node.items()
                    if any(node is pl for pl in changed_playlists)
                }
                self.checked = changed_ids
                for item, node in self.item_to_node.items():
                    self.tree.item(item, text=("☑ " if item in self.checked else "☐ ") + node.name)
                self.run_sync(import_only=False)

            if marker_changed:
                self.write_hotcues(
                    [(p, {"cues": cues, "loops": loops}) for p, cues, loops, _ in marker_changed],
                    quiet=True
                )
                for p, cues, loops, sig in marker_changed:
                    next_state[os.path.normcase(os.path.abspath(p))] = sig
                save_hotcue_state(next_state)

            self.write_log(
                "\n=== SYNCHRONISATION TERMINÉE ===\n"
                f"Playlists mises à jour : {len(changed_playlists)}\n"
                f"Fichiers marqueurs mis à jour : {len(marker_changed)}\n"
                f"Hot Cues écrits : {total_cues}\n"
                f"Saved Loops écrits : {total_loops}"
            )
            messagebox.showinfo(
                "SYNC AUTO terminé",
                f"Playlists mises à jour : {len(changed_playlists)}\n"
                f"Fichiers marqueurs mis à jour : {len(marker_changed)}\n"
                f"Hot Cues écrits : {total_cues}\n"
                f"Saved Loops écrits : {total_loops}\n\n"
                "Tu peux maintenant ouvrir Serato."
            )
            self._add_history({
                "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "playlists": len(changed_playlists),
                "added": total_added,
                "removed": total_removed,
                "cues": total_cues,
                "loops": total_loops
            })
        finally:
            self.checked = original_checked
            for item, node in self.item_to_node.items():
                self.tree.item(item, text=("☑ " if item in self.checked else "☐ ") + node.name)

    def selected_track_paths(self):
        paths = []
        seen = set()
        for pl in self.selected_playlists():
            for p in pl.tracks:
                if p:
                    k = os.path.normcase(os.path.abspath(p))
                    if k not in seen:
                        seen.add(k)
                        paths.append(p)
        return paths

    def hotcue_preview(self):
        if not self.xml_path.get() or not Path(self.xml_path.get()).exists():
            messagebox.showwarning("Hot Cues", "XML Rekordbox introuvable.")
            return
        try:
            cue_map = parse_hot_cues_by_path(self.xml_path.get())
            selected = self.selected_track_paths()
            mp3 = []
            unsupported = 0
            missing = 0
            total_cues = 0

            for p in selected:
                key = os.path.normcase(os.path.abspath(p))
                cues = cue_map.get(key)
                if not cues:
                    continue
                if not Path(p).exists():
                    missing += 1
                    continue
                if Path(p).suffix.lower() != ".mp3":
                    unsupported += 1
                    continue
                mp3.append((p, cues))
                total_cues += len(cues)

            lines = [
                "=== APERÇU HOT CUES ===",
                f"Playlists sélectionnées : {len(self.selected_playlists())}",
                f"MP3 à modifier : {len(mp3)}",
                f"Hot Cues à écrire : {total_cues}",
                f"Formats non pris en charge : {unsupported}",
                f"Fichiers introuvables : {missing}",
                "",
            ]
            for p, cues in mp3[:100]:
                lines.append(f"{Path(p).name} : {len(cues)} Hot Cue(s)")
            if len(mp3) > 100:
                lines.append(f"... + {len(mp3)-100} autre(s)")
            self.write_log("\n".join(lines), clear=True)

            if not mp3:
                messagebox.showinfo("Hot Cues", "Aucun MP3 avec Hot Cues Rekordbox dans les playlists sélectionnées.")
                return

            ok = messagebox.askyesno(
                "Écrire les Hot Cues",
                f"{len(mp3)} MP3 vont être modifiés.\n"
                f"{total_cues} Hot Cues seront écrits.\n\n"
                "Une copie de sauvegarde de CHAQUE MP3 sera créée avant modification.\n"
                "Les Hot Cues Serato existants de ces fichiers seront remplacés.\n\n"
                "Continuer ?"
            )
            if ok:
                self.write_hotcues(mp3)
        except Exception as e:
            messagebox.showerror("Hot Cues", str(e))

    def write_hotcues(self, items, quiet=False):
        backup_root = Path(self.serato_path.get()) / "LBR_Backups" / ("HotCues-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
        backup_root.mkdir(parents=True, exist_ok=True)
        manifest = []
        done = 0
        errors = 0

        for idx, (p, cues) in enumerate(items, 1):
            src = Path(p)
            try:
                # Collision-safe backup name while preserving original basename.
                safe_parent = re.sub(r'[^A-Za-z0-9._-]+', '_', str(src.parent).replace(':',''))
                bdir = backup_root / safe_parent
                bdir.mkdir(parents=True, exist_ok=True)
                backup = bdir / src.name
                n = 1
                while backup.exists():
                    backup = bdir / f"{src.stem}_{n}{src.suffix}"
                    n += 1
                shutil.copy2(src, backup)
                manifest.append(f"{src}\t{backup}")
                if isinstance(cues, dict):
                    inject_serato_markers(src, cues.get("cues", []), cues.get("loops", []))
                else:
                    inject_serato_markers(src, cues, [])
                done += 1
            except Exception as e:
                errors += 1
                self.write_log(f"ERREUR HOT CUES : {src.name} → {e}")

        (backup_root / "manifest.txt").write_text("\n".join(manifest), encoding="utf-8")
        self.write_log(
            f"\n=== MARQUEURS TERMINÉS ===\n"
            f"Fichiers modifiés : {done}\n"
            f"Erreurs : {errors}\n"
            f"Sauvegarde : {backup_root}\n"
            f"Ferme/réouvre ou rescane les fichiers dans Serato si nécessaire."
        )
        self.status.set(f"Marqueurs : {done} fichier(s) modifié(s) • {errors} erreur(s)")
        if not quiet:
            messagebox.showinfo(
                "Marqueurs terminés",
                f"{done} fichier(s) modifié(s).\n{errors} erreur(s).\n\n"
                f"Sauvegardes :\n{backup_root}"
            )

    def make_backup(self):
        serato = Path(self.serato_path.get())
        sub = serato / "Subcrates"
        if not sub.exists() or not any(sub.iterdir()):
            return None
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        dest = serato / "LBR_Backups" / stamp / "Subcrates"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(sub, dest)
        return dest.parent

    def serato_volume(self):
        p = Path(self.serato_path.get())
        drive = p.drive
        return drive.upper() if drive else ""

    def validate_crate_audio_path(self, p):
        """Retourne True uniquement si le morceau est sur le même volume que _Serato_."""
        try:
            audio_drive = Path(p).drive.upper()
            serato_drive = self.serato_volume()
            return bool(audio_drive and serato_drive and audio_drive == serato_drive)
        except Exception:
            return False

    def force_rewrite(self):
        selected = self.selected_playlists()
        if not selected:
            messagebox.showwarning("Sélection", "Aucune playlist sélectionnée.")
            return

        names = "\n".join("• " + p.display_path for p in selected[:10])
        if len(selected) > 10:
            names += f"\n• ... + {len(selected)-10} autre(s)"

        if not messagebox.askyesno(
            "Forcer la réécriture",
            "Les crates sélectionnés vont être RÉÉCRITS même s'ils sont marqués IDENTIQUE.\n\n"
            + names +
            "\n\nUne sauvegarde des crates actuels sera créée avant l'écriture.\n"
            "Aucun fichier audio ne sera modifié.\n\nContinuer ?"
        ):
            return

        try:
            backup = self.make_backup()
            rewritten = missing = 0
            lines = ["=== RÉÉCRITURE FORCÉE ==="]

            for pl in selected:
                dest = self.crate_path(pl)
                valid = []
                pl_missing = 0

                for p in pl.tracks:
                    if p and Path(p).exists() and self.validate_crate_audio_path(p):
                        valid.append(p)
                    else:
                        pl_missing += 1

                missing += pl_missing
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(make_crate(valid))
                rewritten += 1
                lines.append(f"RÉÉCRIT : {pl.display_path} ({len(valid)} titres)")
                if pl_missing:
                    lines.append(f"  ATTENTION : {pl_missing} fichier(s) introuvable(s) ignoré(s)")

            lines += [
                "",
                f"Crates réécrits : {rewritten}",
                f"Fichiers introuvables : {missing}",
                f"Sauvegarde : {backup if backup else 'aucune crate existante'}"
            ]
            self.write_log("\n".join(lines), clear=True)
            self.refresh_statuses()
            self.status.set(f"RÉÉCRITURE terminée • {rewritten} crate(s) • {missing} fichier(s) introuvable(s)")
            messagebox.showinfo("Réécriture terminée", self.status.get())
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def run_sync(self, import_only=False):
        selected = self.selected_playlists()
        if not selected:
            messagebox.showwarning("Sélection", "Aucune playlist sélectionnée.")
            return

        serato = Path(self.serato_path.get())
        sub = serato / "Subcrates"
        sub.mkdir(parents=True, exist_ok=True)

        mode = "IMPORT" if import_only else "SYNCHRONISATION"
        if not import_only:
            ok = messagebox.askyesno(
                "Synchroniser",
                "Le mode SYNCHRONISER remplace le contenu des crates sélectionnés\n"
                "pour qu'ils correspondent aux playlists Rekordbox.\n\n"
                "Aucun fichier audio ne sera supprimé.\n\nContinuer ?"
            )
            if not ok:
                return

        try:
            backup = self.make_backup()
            created = updated = identical = missing = 0
            lines = [f"=== {mode} ==="]

            for pl in selected:
                dest = self.crate_path(pl)
                status, _, _ = self.compare_playlist(pl)

                if import_only and dest.exists():
                    lines.append(f"IGNORÉ : {pl.display_path} (crate déjà existant)")
                    continue

                valid = []
                pl_missing = 0
                for p in pl.tracks:
                    if p and Path(p).exists() and self.validate_crate_audio_path(p):
                        valid.append(p)
                    else:
                        pl_missing += 1
                missing += pl_missing

                if status == "IDENTIQUE":
                    identical += 1
                    lines.append(f"IDENTIQUE : {pl.display_path}")
                    continue

                dest.write_bytes(make_crate(valid))
                if status == "À CRÉER":
                    created += 1
                    lines.append(f"CRÉÉ : {pl.display_path} ({len(valid)} titres)")
                else:
                    updated += 1
                    lines.append(f"MAJ : {pl.display_path} ({len(valid)} titres)")
                if pl_missing:
                    lines.append(f"  ATTENTION : {pl_missing} fichier(s) introuvable(s) ignoré(s)")

            lines += [
                "",
                f"Créés : {created}",
                f"Mis à jour : {updated}",
                f"Identiques : {identical}",
                f"Fichiers introuvables : {missing}",
                f"Sauvegarde : {backup if backup else 'aucune crate existante'}"
            ]
            self.write_log("\n".join(lines), clear=True)
            self.refresh_statuses()
            self.status.set(f"{mode} terminé • {created} créé(s) • {updated} mis à jour • {missing} fichier(s) introuvable(s)")
            messagebox.showinfo("Terminé", self.status.get())
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def restore_last_backup(self):
        serato = Path(self.serato_path.get())
        backups = serato / "LBR_Backups"
        if not backups.exists():
            messagebox.showinfo("Sauvegarde", "Aucune sauvegarde LBR trouvée.")
            return
        candidates = sorted([p for p in backups.iterdir() if p.is_dir()], reverse=True)
        if not candidates:
            messagebox.showinfo("Sauvegarde", "Aucune sauvegarde LBR trouvée.")
            return
        latest = candidates[0] / "Subcrates"
        if not latest.exists():
            messagebox.showerror("Sauvegarde", "La dernière sauvegarde ne contient pas Subcrates.")
            return

        if not messagebox.askyesno(
            "Restaurer",
            f"Restaurer la dernière sauvegarde ?\n\n{latest.parent.name}\n\n"
            "Les crates actuels seront remplacés."
        ):
            return

        current = serato / "Subcrates"
        safety = serato / "LBR_Backups" / ("avant-restauration-" + datetime.now().strftime("%Y%m%d-%H%M%S")) / "Subcrates"
        if current.exists():
            safety.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(current, safety)
            shutil.rmtree(current)
        shutil.copytree(latest, current)
        self.status.set("Dernière sauvegarde restaurée.")
        self.write_log(f"RESTAURATION : {latest.parent.name}\nCopie de sécurité de l'état précédent : {safety.parent}")
        self.refresh_statuses()
        messagebox.showinfo("Restauré", "La dernière sauvegarde a été restaurée.")

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from LBR_DJ_Library_Manager_FINAL import LBRManager
    LBRManager().mainloop()
