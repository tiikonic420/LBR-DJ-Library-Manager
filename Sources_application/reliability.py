"""V4.1 services. No music discovery, downloads or writes at import time."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import uuid


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.lbr-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


class Conflict(RuntimeError):
    pass


class Cancelled(RuntimeError):
    pass


class BackupStore:
    """Full file snapshots; manifest is committed only after every copy verifies.

    Music databases must be closed before snapshotting (including WAL sidecars).
    Restore never removes a target first. A conflicting target is refused.
    """
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()

    def _folder(self, identifier):
        if not isinstance(identifier, str) or len(identifier) != 32 or any(c not in '0123456789abcdef' for c in identifier):
            raise ValueError('Identifiant de sauvegarde invalide')
        folder = self.root / identifier
        if folder.is_symlink():
            raise ValueError('Sauvegarde liée refusée')
        return folder

    def load(self, identifier):
        data = json.loads((self._folder(identifier) / 'manifest.json').read_text(encoding='utf-8'))
        if data.get('id') != identifier or data.get('schema') != 1:
            raise ValueError('Manifeste non reconnu')
        for index, item in enumerate(data['files']):
            if item['blob'] != f'{index:08d}.bin' or not Path(item['path']).is_absolute():
                raise ValueError('Chemin de manifeste invalide')
        return data

    def create(self, paths, label='Sauvegarde', checkpoint=lambda: None):
        with self.lock:
            identifier = uuid.uuid4().hex
            folder = self._folder(identifier)
            folder.mkdir()
            files = []
            # A partial folder has no manifest and is never offered for restoration.
            try:
                seen = set()
                for path in paths:
                    checkpoint()
                    raw = Path(path).absolute()
                    if raw.is_symlink():
                        raise ValueError('Liens symboliques refusés : ' + str(raw))
                    src = raw.resolve()
                    if src in seen:
                        continue
                    seen.add(src)
                    if self.root == src or self.root in src.parents:
                        raise ValueError('Une sauvegarde ne peut pas se sauvegarder elle-même')
                    exists = src.exists()
                    if exists and not src.is_file():
                        raise ValueError('Fichier régulier requis : ' + str(src))
                    entry = {'path': str(src), 'existed': exists, 'blob': f'{len(files):08d}.bin',
                             'sha256': None, 'expected': None, 'state': 'prepared'}
                    if exists:
                        before = digest(src)
                        shutil.copy2(src, folder / entry['blob'])
                        if digest(src) != before or digest(folder / entry['blob']) != before:
                            raise Conflict('Fichier modifié pendant la sauvegarde : ' + str(src))
                        entry['sha256'] = entry['expected'] = before
                    files.append(entry)
                data = {'schema': 1, 'id': identifier, 'label': label, 'created': now(), 'files': files}
                atomic_json(folder / 'manifest.json', data)
                self.verify(identifier)
                return identifier
            except BaseException:
                shutil.rmtree(folder, ignore_errors=True)
                raise

    def verify(self, identifier):
        data = self.load(identifier)
        folder = self._folder(identifier)
        for item in data['files']:
            if item['existed']:
                blob = folder / item['blob']
                if blob.is_symlink() or digest(blob) != item['sha256']:
                    raise Conflict('Sauvegarde corrompue : ' + item['path'])
        return data

    def assert_current(self, identifier):
        data = self.verify(identifier)
        for item in data['files']:
            p = Path(item['path'])
            actual = digest(p) if p.exists() else None
            if p.is_symlink() or actual != item['expected']:
                raise Conflict('Le fichier a changé depuis la préparation : ' + str(p))
        return data

    def mark(self, identifier, state='completed'):
        with self.lock:
            data = self.load(identifier)
            for item in data['files']:
                p = Path(item['path'])
                item['expected'] = digest(p) if p.exists() else None
                item['state'] = state
            data['updated'] = now()
            atomic_json(self._folder(identifier) / 'manifest.json', data)

    def list(self):
        result = []
        for p in self.root.glob('*/manifest.json'):
            try:
                result.append(self.load(p.parent.name))
            except (OSError, ValueError, KeyError):
                continue
        return sorted(result, key=lambda x: x['created'], reverse=True)

    def restore(self, identifier, selected=None, checkpoint=lambda: None):
        """Preflight all selected files before any replacement; partial commits journaled.

        Original absences are never restored by deleting new files. The explicit
        removal of newly created references belongs in a separate user plan.
        """
        with self.lock:
            data = self.verify(identifier)
            requested = None if selected is None else {str(Path(p).resolve()) for p in selected}
            entries = [e for e in data['files'] if requested is None or e['path'] in requested]
            if requested is not None and requested != {e['path'] for e in entries}:
                raise ValueError('Sélection absente du manifeste')
            for item in entries:
                checkpoint()
                target = Path(item['path'])
                actual = digest(target) if target.exists() else None
                if target.is_symlink() or actual != item['expected']:
                    raise Conflict('Conflit de restauration : ' + str(target))
                if not item['existed']:
                    raise Conflict('Création conservée : suppression automatique refusée : ' + str(target))
            staged = []
            try:
                # Prepare all restored bytes and an emergency snapshot first.
                self.create([e['path'] for e in entries], 'Avant restauration ' + identifier)
                for item in entries:
                    checkpoint()
                    target = Path(item['path'])
                    fd, temp = tempfile.mkstemp(prefix='.lbr-restore-', dir=target.parent)
                    os.close(fd)
                    staged.append((item, Path(temp)))
                    shutil.copy2(self._folder(identifier) / item['blob'], temp)
                    if digest(temp) != item['sha256']:
                        raise Conflict('Copie de restauration invalide')
                for item, temp in staged:
                    checkpoint()
                    target = Path(item['path'])
                    actual = digest(target) if target.exists() else None
                    if actual != item['expected']:
                        raise Conflict('Conflit pendant la restauration : ' + str(target))
                    os.replace(temp, target)
                    item['expected'] = item['sha256']
                    item['state'] = 'restored'
                    atomic_json(self._folder(identifier) / 'manifest.json', data)
                return len(entries)
            finally:
                for _, temp in staged:
                    temp.unlink(missing_ok=True)

    @contextmanager
    def protect(self, paths, label='Écriture', checkpoint=lambda: None):
        identifier = self.create(paths, label, checkpoint)
        self.assert_current(identifier)
        checkpoint()
        try:
            yield identifier
        except BaseException:
            # Only the completed callback owns writes during this protected scope.
            # Capture failed postimages, then restore originals; keep evidence.
            self.mark(identifier, 'failed')
            self.restore(identifier)
            raise
        else:
            self.mark(identifier)


class Journal:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self._db = sqlite3.connect(self.path, timeout=15, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        # Keep every task durable without recreating a rollback journal on each
        # UI refresh. FULL retains a sync at each WAL transaction commit.
        if self._db.execute('PRAGMA journal_mode=WAL').fetchone()[0] != 'wal':
            self.close()
            raise RuntimeError('Journal WAL indisponible')
        self._db.execute('PRAGMA synchronous=FULL')
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, owner TEXT, title TEXT, state TEXT, done INTEGER, total INTEGER, created TEXT, updated TEXT, detail TEXT)')
            db.execute("UPDATE tasks SET state='interrupted', updated=? WHERE state IN ('running','pending')", (now(),))

    @contextmanager
    def connect(self):
        with self.lock:
            db = self._db
            if db is None:
                raise RuntimeError('Journal fermé')
            with db:
                yield db

    def close(self):
        with self.lock:
            if self._db is not None:
                self._db.close()
                self._db = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def start(self, owner, title):
        identifier = uuid.uuid4().hex
        with self.connect() as db:
            db.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?)', (identifier, owner, title, 'running', 0, 0, now(), now(), ''))
        return identifier

    def update(self, identifier, state='running', done=0, total=0, detail=''):
        if state not in {'pending', 'running', 'completed', 'failed', 'cancelled', 'interrupted'}:
            raise ValueError('État inconnu')
        with self.connect() as db:
            db.execute('UPDATE tasks SET state=?,done=?,total=?,updated=?,detail=? WHERE id=?', (state, done, total, now(), str(detail), identifier))

    def list(self, limit=200):
        with self.connect() as db:
            return [dict(row) for row in db.execute('SELECT * FROM tasks ORDER BY created DESC LIMIT ?', (max(1, min(limit, 1000)),))]

    def export(self, path):
        atomic_json(path, {'schema': 1, 'exported': now(), 'tasks': self.list(1000)})


def preview(module, changes, skipped=()):
    """A pure data contract; no directory creation or file writes."""
    return {'schema': 1, 'module': module, 'changes': list(changes), 'skipped': list(skipped)}


def diagnose_rbsync(candidates=(), runner=None):
    """Explicit read-only diagnostic: version, package metadata, CLI --help.

    Never calls pip, starts installation, or opens a DJ database.
    """
    import subprocess
    import platform
    runner = runner or subprocess.run
    results = []
    code = """import sys,json,importlib.metadata as m
try:
    version=m.version('rekordbox-playlist-sync')
except m.PackageNotFoundError:
    try:
        version=m.version('rbsync')
    except m.PackageNotFoundError:
        from rbsync import __version__ as version
print(json.dumps({'python':list(sys.version_info[:3]),'rbsync':version}))
"""
    for candidate in dict.fromkeys(str(Path(p)) for p in candidates if p):
        row = {'python_path': candidate, 'exists': Path(candidate).is_file()}
        if row['exists']:
            try:
                cp = runner([candidate, '-c', code], capture_output=True, text=True, timeout=20)
                row.update(returncode=cp.returncode, stdout=cp.stdout, stderr=cp.stderr)
                if cp.returncode == 0:
                    info = json.loads(cp.stdout.strip().splitlines()[-1])
                    row.update(info)
                    row['python313'] = info['python'][:2] == [3, 13]
                    help_result = runner([candidate, '-m', 'rbsync', '--help'], capture_output=True, text=True, timeout=20)
                    row['help_returncode'] = help_result.returncode
                    row['help_stderr'] = help_result.stderr
                    row['version_supported'] = info.get('rbsync') == '0.2.0'
                    row['compatible'] = row['python313'] and row['version_supported'] and help_result.returncode == 0
            except Exception as exc:
                row['error'] = str(exc)
        results.append(row)
    return {'created': now(), 'host': platform.platform(), 'current_python': sys.version,
            'candidates': results, 'repair': 'Créer un venv Python 3.13 et installer une révision rbsync validée après autorisation explicite. Aucun changement système effectué.'}
