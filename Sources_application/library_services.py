"""Read-only music catalogue and explicit plans for V4.5/V5.0.

All operations receive authorized roots. This module never opens a Rekordbox DB.
"""
from contextlib import contextmanager
from pathlib import Path
import json
import os
import re
import sqlite3
import unicodedata
from reliability import digest, atomic_json, Conflict

FIELDS = {'artist', 'title', 'album', 'genre', 'year', 'bpm', 'key', 'format', 'path'}
AUDIO_EXTS = {'.mp3', '.aac', '.m4a', '.mp4', '.flac', '.wav', '.aif', '.aiff', '.ogg', '.opus', '.wma', '.asf', '.ape', '.wv', '.mpc'}


def authorized(path, roots):
    p = Path(path).resolve()
    if not any(p == Path(r).resolve() or Path(r).resolve() in p.parents for r in roots):
        raise PermissionError('Chemin hors des dossiers autorisés : ' + str(p))
    return p


def audio_info(path):
    from mutagen import File
    import tag_engine
    p = Path(path)
    result = {'path': str(p.resolve()), 'format': p.suffix.lower().lstrip('.'), 'error': '',
              'duration': None, 'bitrate': None, 'sample_rate': None, 'bits': None, 'channels': None}
    try:
        audio = File(str(p), easy=False)
        if audio is None:
            raise ValueError('Format illisible ou non reconnu')
        info = audio.info
        for field, attr in [('duration', 'length'), ('bitrate', 'bitrate'), ('sample_rate', 'sample_rate'), ('bits', 'bits_per_sample'), ('channels', 'channels')]:
            result[field] = getattr(info, attr, None)
        result['codec'] = getattr(info, 'codec', type(info).__name__)
        result.update(tag_engine.read_tags(str(p)))
        raw_year = str(result.pop('date', ''))[:4]
        result['year'] = int(raw_year) if raw_year.isdigit() else None
        try:
            result['bpm'] = float(result.get('bpm', ''))
        except (ValueError, TypeError):
            result['bpm'] = None
        result['anomalies'] = []
        if not result['duration'] or result['duration'] <= 0:
            result['anomalies'].append('Durée absente ou nulle')
        if result['sample_rate'] and result['sample_rate'] < 22050:
            result['anomalies'].append('Fréquence basse : vérifier selon usage')
        if result['channels'] and result['channels'] > 2:
            result['anomalies'].append('Multicanal : vérifier la compatibilité DJ')
    except Exception as exc:
        result['error'] = str(exc)
    return result


class Catalogue:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS tracks(
                path TEXT PRIMARY KEY, artist TEXT DEFAULT '', title TEXT DEFAULT '',
                album TEXT DEFAULT '', genre TEXT DEFAULT '', year INTEGER,
                bpm REAL, key TEXT DEFAULT '', format TEXT, duration REAL, size INTEGER,
                mtime INTEGER, sha256 TEXT, data TEXT NOT NULL, search_text TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_artist ON tracks(artist COLLATE NOCASE);
            CREATE INDEX IF NOT EXISTS idx_title ON tracks(title COLLATE NOCASE);
            CREATE INDEX IF NOT EXISTS idx_bpm ON tracks(bpm);
            CREATE INDEX IF NOT EXISTS idx_year ON tracks(year);
            CREATE INDEX IF NOT EXISTS idx_hash ON tracks(sha256);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def upsert(self, rows):
        values = []
        for row in rows:
            values.append((row['path'], row.get('artist', ''), row.get('title', ''), row.get('album', ''), row.get('genre', ''), row.get('year'), row.get('bpm'), row.get('key', ''), row.get('format', ''), row.get('duration'), row.get('size'), row.get('mtime'), row.get('sha256'), json.dumps(row, ensure_ascii=False), ' '.join(str(row.get(f, '')) for f in ('artist', 'title', 'album', 'genre', 'year', 'path')).casefold()))
        with self.connect() as db:
            db.executemany('INSERT OR REPLACE INTO tracks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', values)

    def index(self, roots, checkpoint=lambda: None, progress=lambda done, total: None):
        roots = [Path(r).resolve() for r in roots]
        if not roots or any(not r.is_dir() for r in roots):
            raise ValueError('Choisir au moins un dossier existant')
        changed = unchanged = seen = 0
        batch = []
        # Streaming traversal: no list of 100,000 filenames on the UI thread.
        visited = set()
        for root in roots:
            for directory, dirs, names in os.walk(root, followlinks=False):
                dirs[:] = [d for d in dirs if not (Path(directory) / d).is_symlink()]
                for name in names:
                    checkpoint()
                    p = Path(directory) / name
                    if p.is_symlink() or p.suffix.lower() not in AUDIO_EXTS:
                        continue
                    p = authorized(p, roots)
                    if str(p) in visited:
                        continue
                    visited.add(str(p))
                    stat = p.stat()
                    with self.connect() as db:
                        old = db.execute('SELECT size,mtime FROM tracks WHERE path=?', (str(p),)).fetchone()
                    seen += 1
                    if old and old['size'] == stat.st_size and old['mtime'] == stat.st_mtime_ns:
                        unchanged += 1
                    else:
                        row = audio_info(p)
                        after = p.stat()
                        if (stat.st_size, stat.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                            raise Conflict('Fichier modifié pendant indexation : ' + str(p))
                        row.update(size=stat.st_size, mtime=stat.st_mtime_ns, sha256=None)
                        batch.append(row)
                        changed += 1
                    if len(batch) >= 100:
                        self.upsert(batch)
                        batch.clear()
                    if seen % 100 == 0:
                        progress(seen, 0)
        self.upsert(batch)
        progress(seen, seen)
        return {'seen': seen, 'changed': changed, 'unchanged': unchanged,
                'note': 'Références absentes conservées pour la réparation des chemins.'}

    def search(self, query='', filters=None, page=0, page_size=100, rules=None):
        filters = filters or {}
        clauses, params = [], []
        if query:
            q = '%' + query.casefold().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
            clauses.append("search_text LIKE ? ESCAPE '\\'")
            params.append(q)
        for field, value in filters.items():
            if field not in FIELDS | {'bpm_min', 'bpm_max'}:
                raise ValueError('Filtre inconnu : ' + field)
            if field in ('bpm_min', 'bpm_max'):
                clauses.append('bpm ' + ('>=' if field == 'bpm_min' else '<=') + ' ?')
                params.append(float(value))
            else:
                clauses.append(field + ' = ?')
                params.append(value)
        if rules:
            expr, values = compile_rules(rules)
            clauses.append(expr)
            params.extend(values)
        where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
        limit = min(500, max(1, int(page_size)))
        with self.connect() as db:
            rows = db.execute('SELECT * FROM tracks' + where + ' ORDER BY path LIMIT ? OFFSET ?', [*params, limit, max(0, int(page)) * limit]).fetchall()
        return [dict(row) for row in rows]

    def stats(self):
        with self.connect() as db:
            return dict(db.execute("SELECT count(*) AS tracks, count(DISTINCT NULLIF(artist, '')) AS artists, count(DISTINCT NULLIF(genre, '')) AS genres, sum(duration) AS duration FROM tracks").fetchone())

    def duplicates(self, roots, checkpoint=lambda: None):
        exact, probable = {}, {}
        with self.connect() as db:
            rows = db.execute('SELECT * FROM tracks ORDER BY path').fetchall()
        sizes = {}
        for row in rows:
            checkpoint()
            p = authorized(row['path'], roots)
            if not p.is_file() or p.is_symlink():
                continue
            sizes.setdefault(p.stat().st_size, []).append(row)
            artist = normalize(row['artist'])
            title = normalize(row['title'])
            if artist and title:
                probable.setdefault((artist, title), []).append(row)
        for group in sizes.values():
            if len(group) < 2:
                continue
            for row in group:
                checkpoint()
                h = digest(row['path'])
                exact.setdefault(h, []).append(row['path'])
        exact_groups = [v for v in exact.values() if len(v) > 1]
        exact_sets = [set(v) for v in exact_groups]
        probable_groups = []
        for group in probable.values():
            if len(group) < 2:
                continue
            # Duration tolerance is explicit. Unknown durations do not imply a match.
            for i, a in enumerate(group):
                for b in group[i + 1:]:
                    pair = {a['path'], b['path']}
                    if not any(pair <= s for s in exact_sets) and a['duration'] and b['duration'] and abs(a['duration'] - b['duration']) <= 2:
                        probable_groups.append({'paths': sorted(pair), 'confidence': 'probable', 'reason': 'Artiste/titre normalisés et durée ±2 s ; aucune preuve acoustique'})
        return {'exact_sha256': exact_groups, 'probable': probable_groups, 'deletions': 0}

    def missing(self, roots, checkpoint=lambda: None):
        with self.connect() as db:
            paths = [r[0] for r in db.execute('SELECT path FROM tracks')]
        result = []
        for p in paths:
            checkpoint()
            authorized(p, roots)
            if not Path(p).is_file():
                result.append(p)
        return result


def normalize(text):
    return ' '.join(unicodedata.normalize('NFKC', str(text)).casefold().split())


def compile_rules(node, depth=0):
    if depth > 8:
        raise ValueError('Règles trop imbriquées')
    if not isinstance(node, dict):
        raise ValueError('Règle invalide')
    if 'rules' in node:
        mode = node.get('mode', 'AND')
        if mode not in ('AND', 'OR') or not 1 <= len(node['rules']) <= 50:
            raise ValueError('Groupe de règles invalide')
        parts, params = [], []
        for child in node['rules']:
            sql, values = compile_rules(child, depth + 1)
            parts.append(sql)
            params.extend(values)
        return '(' + (' ' + mode + ' ').join(parts) + ')', params
    field, op, value = node.get('field'), node.get('op'), node.get('value')
    if field not in FIELDS:
        raise ValueError('Champ de règle inconnu')
    if op in ('=', '!=', '<', '<=', '>', '>='):
        return f'{field} {op} ?', [value]
    if op == 'contains':
        return f"{field} LIKE ? ESCAPE '\\'", ['%' + str(value).replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%']
    raise ValueError('Opérateur inconnu')


def propose_paths(missing, roots, checkpoint=lambda: None):
    candidates = {}
    for root in roots:
        root = authorized(root, roots)
        for directory, dirs, names in os.walk(root, followlinks=False):
            dirs[:] = [d for d in dirs if not (Path(directory) / d).is_symlink()]
            for name in names:
                checkpoint()
                p = Path(directory) / name
                if p.suffix.lower() in AUDIO_EXTS and not p.is_symlink():
                    candidates.setdefault(name.casefold(), []).append(str(authorized(p, roots)))
    return [{'before': old, 'candidates': candidates.get(Path(old).name.casefold(), []),
             'confidence': 'nom unique, à vérifier' if len(candidates.get(Path(old).name.casefold(), [])) == 1 else 'ambigu ou absent'} for old in missing]


def repair_xml(source, replacements, roots, store, output=None):
    """Explicit path repair for exported Rekordbox XML only, never master.db.

    All non-Location XML attributes and marker elements retain their values.
    A separate output is recommended; replacing the export requires confirmation
    at the controller level and is protected here by a verified snapshot.
    """
    import xml.etree.ElementTree as ET
    from urllib.parse import unquote, urlparse
    source = Path(source).resolve()
    output = Path(output).resolve() if output else source
    if source.suffix.lower() != '.xml' or output.suffix.lower() != '.xml':
        raise ValueError('La réparation exige une source et une destination XML')
    tree = ET.parse(source)
    changes = []
    for track in tree.getroot().findall('.//COLLECTION/TRACK'):
        loc = track.get('Location', '')
        old = unquote(urlparse(loc).path) if loc.startswith('file:') else loc
        if re.match(r'^/[A-Za-z]:', old):
            old = old[1:]
        replacement = replacements.get(old)
        if replacement:
            new = authorized(replacement, roots)
            if not new.is_file() or Path(old).is_file():
                raise Conflict('Ancien chemin existant ou nouvelle cible absente')
            changes.append({'before': loc, 'after': new.as_uri()})
            track.set('Location', new.as_uri())
    if not changes:
        return {'changes': []}
    output.parent.mkdir(parents=True, exist_ok=True)
    with store.protect([output], 'Réparation XML'):
        import tempfile
        fd, temp = tempfile.mkstemp(prefix='.lbr-xml-', dir=output.parent)
        os.close(fd)
        try:
            tree.write(temp, encoding='utf-8', xml_declaration=True)
            ET.parse(temp)
            os.replace(temp, output)
        finally:
            Path(temp).unlink(missing_ok=True)
    return {'changes': changes, 'output': str(output)}


def bounded_regex(pattern, replacement, text):
    import subprocess
    import sys
    if len(pattern) > 256 or len(text) > 8192:
        raise ValueError('Expression ou texte trop long')
    code = "import re,json,sys;p,r,t=json.load(sys.stdin);print(json.dumps(re.sub(p,r,t)))"
    try:
        cp = subprocess.run([sys.executable, '-c', code], input=json.dumps([pattern, replacement, text]), capture_output=True, text=True, timeout=2,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except subprocess.TimeoutExpired as exc:
        raise ValueError('Expression régulière trop coûteuse (limite 2 secondes)') from exc
    if cp.returncode:
        raise ValueError('Expression régulière invalide : ' + cp.stderr[-600:])
    return json.loads(cp.stdout)


def batch_plan(paths, transformations, roots, checkpoint=lambda: None):
    import tag_engine
    changes = []
    for path in paths:
        checkpoint()
        p = authorized(path, roots)
        tags = tag_engine.read_tags(str(p))
        result = {}
        for transform in transformations:
            field, action = transform.get('field'), transform.get('action')
            if field not in tag_engine.FIELDS:
                raise ValueError('Champ de tag non pris en charge')
            old = str(result.get(field, tags.get(field, '')))
            if action == 'set':
                value = str(transform.get('value', ''))
            elif action == 'replace':
                value = old.replace(transform['search'], transform.get('replacement', ''))
            elif action == 'regex':
                value = bounded_regex(transform['search'], transform.get('replacement', ''), old)
            elif action == 'normalize':
                value = ' '.join(unicodedata.normalize('NFKC', old).split())
            elif action == 'filename':
                extracted = tag_engine.parse_filename(p.name, transform['pattern'])
                if not extracted or field not in extracted:
                    continue
                value = extracted[field]
            else:
                raise ValueError('Transformation inconnue')
            if value != tags.get(field, ''):
                result[field] = value
        if result:
            changes.append({'path': str(p), 'sha256': digest(p),
                            'before': {k: tags.get(k, '') for k in result}, 'after': result})
    return {'schema': 1, 'module': 'TagStudio', 'changes': changes, 'skipped': []}


def apply_batch(plan, roots, store, checkpoint=lambda: None, progress=lambda done, total: None):
    import tag_engine
    entries = plan['changes']
    for entry in entries:
        checkpoint()
        p = authorized(entry['path'], roots)
        if digest(p) != entry['sha256']:
            raise Conflict('Aperçu obsolète : ' + str(p))
    with store.protect([e['path'] for e in entries], 'Tags par lots', checkpoint) as identifier:
        for n, entry in enumerate(entries, 1):
            checkpoint()
            if digest(entry['path']) != entry['sha256']:
                raise Conflict('Aperçu obsolète pendant le lot : ' + entry['path'])
            tag_engine.write_tags(entry['path'], entry['after'])
            readback = tag_engine.read_tags(entry['path'])
            if any(str(readback.get(k, '')) != str(v) for k, v in entry['after'].items()):
                raise Conflict('Vérification des tags échouée')
            progress(n, len(entries))
    return identifier


def export_playlist(catalogue, rules, destination, roots, store, checkpoint=lambda: None):
    paths, page = [], 0
    while True:
        checkpoint()
        rows = catalogue.search(rules=rules, page=page, page_size=500)
        if not rows:
            break
        for row in rows:
            p = authorized(row['path'], roots)
            if p.is_file():
                paths.append(str(p))
        page += 1
    destination = Path(destination)
    if destination.suffix.lower() not in ('.m3u', '.m3u8'):
        raise ValueError('Destination M3U/M3U8 requise')
    if any('\n' in p or '\r' in p for p in paths):
        raise ValueError('Chemin contenant un saut de ligne')
    with store.protect([destination], 'Playlist intelligente'):
        from reliability import atomic_json
        import tempfile
        fd, temp = tempfile.mkstemp(prefix='.lbr-playlist-', dir=destination.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                stream.write('#EXTM3U\n' + '\n'.join(paths) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, destination)
        finally:
            Path(temp).unlink(missing_ok=True)
    return {'destination': str(destination), 'tracks': len(paths)}
