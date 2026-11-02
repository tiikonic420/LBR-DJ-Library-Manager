"""Windows Explorer file drops, scoped to Tag Studio; no engine or tag writes."""
import ctypes
from ctypes import wintypes
import importlib
import os
import queue
from pathlib import Path
import sys


def audio_paths(inputs, extensions, checkpoint):
    """Enumerate explicit local input, without following directory links/junctions."""
    seen = set()
    result = []
    def add(path):
        if path.suffix.lower() not in extensions or not path.is_file():
            return
        key = os.path.normcase(os.path.abspath(path))
        if key not in seen:
            seen.add(key)
            result.append(str(path.absolute()))
            if len(result) > 100000:
                raise ValueError('Dépôt trop volumineux : limite de 100 000 fichiers. Choisis un sous-dossier.')
    for raw in inputs:
        checkpoint()
        path = Path(raw)
        if not path.is_absolute() or str(path).startswith(('\\\\', '//')):
            raise ValueError('Dépose des fichiers ou dossiers locaux avec un chemin absolu.')
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            continue
        if not path.exists():
            raise FileNotFoundError(str(path))
        if path.is_dir():
            def fail(error):raise error
            for parent, dirs, files in os.walk(path, followlinks=False, onerror=fail):
                checkpoint()
                dirs[:] = sorted(d for d in dirs if not (Path(parent)/d).is_symlink()
                                 and not (hasattr(Path(parent)/d, 'is_junction') and (Path(parent)/d).is_junction()))
                for name in sorted(files):
                    checkpoint()
                    child = Path(parent)/name
                    if not child.is_symlink():add(child)
        else:
            add(path)
    return result


class TagStudioDrop:
    def __init__(self, app):
        self.app = app
        self.host = app.winfo_toplevel()
        self.windows = set()
        self.callback = None
        self.pending = queue.SimpleQueue()
        self._poll_job = None
        self._closed = False
        if sys.platform == 'win32':
            self._install()
            self.app.bind('<Destroy>', self._destroyed, add='+')
            self._poll_job = self.app.after(50, self._poll)

    def _destroyed(self, event):
        if event.widget is self.app:
            self._closed = True
            if self._poll_job is not None:
                self.app.after_cancel(self._poll_job)
                self._poll_job = None

    def _poll(self):
        """Only a normal Tk callback may create Tcl commands or schedule work."""
        self._poll_job = None
        if self._closed or self.host.hub.stopped:
            return
        for _ in range(16):
            try:
                kind, value = self.pending.get_nowait()
            except queue.Empty:
                break
            if kind == 'drop':
                self.receive(value)
            else:
                self.host.report_callback_exception(*value)
        self._poll_job = self.app.after(50, self._poll)

    def receive(self, paths):
        """Called on Tk thread after native drop resources have been released."""
        if self.host.current != 'TagStudio' or self.host.hub.busy or self.host.hub.stopped:
            self.host.task_detail.set('Dépôt refusé : ouvre Tag Studio et attends la fin du traitement en cours.')
            return False
        if self.host.grab_current() is not None:
            return False
        paths = tuple(paths)
        self.host.hub.run('TagStudio', 'Lecture des fichiers déposés', self._load, paths)
        return True

    def _load(self, paths):
        from reliability import Cancelled
        try:
            self._load_files(paths)
        except Cancelled:
            self.host.hub.post(self.app.status.set, 'Dépôt annulé au point sûr ; liste conservée.')

    def _load_files(self, paths):
        module = importlib.import_module('tag_studio')
        workspace = self.host.workspace
        files = audio_paths(paths, module.EXTS, workspace.checkpoint)
        known = {os.path.normcase(os.path.abspath(path)) for path in self.app.rows}
        additions, failures = {}, []
        for number, path in enumerate(files):
            workspace.checkpoint()
            if os.path.normcase(os.path.abspath(path)) not in known:
                try:
                    tags = module.read_tags(path)
                    tags.update(file=Path(path).name, path=path, serato=module.serato_info(path),
                                rekordbox=self.app.rb.get(str(Path(path)).lower(), 'Non analysé'))
                    additions[path] = tags
                except Exception as error:
                    failures.append((path, str(error)))
            if number % 100 == 0:workspace.progress(number, len(files))
        workspace.checkpoint()
        def commit():
            self.app.rows.update(additions)
            self.app.active_filter = ''
            self.app.folders.delete(0, 'end')
            self.app.folders.insert('end', 'Tous les dossiers')
            if self.app.rows:
                try:
                    self.app.folder = os.path.commonpath([str(Path(p).parent) for p in self.app.rows])
                except ValueError:
                    self.app.folder = ''  # Multiple volumes: keep all tracks, no relative filter.
                if self.app.folder:
                    folders = sorted({str(Path(p).parent.relative_to(self.app.folder)) for p in self.app.rows})
                    for folder in folders:self.app.folders.insert('end', folder)
            for path, error in failures:self.app.logmsg('Dépôt ignoré : ' + path + ' : ' + error)
            self.app.logmsg(f'Dépôt : {len(additions)} ajoutés, {len(failures)} illisibles ; aucun fichier modifié.')
        self.host.hub.ui(commit)
        self.app.populate()
        workspace.progress(len(files), len(files))

    def _install(self):
        self.shell = ctypes.WinDLL('shell32', use_last_error=True)
        self.controls = ctypes.WinDLL('comctl32', use_last_error=True)
        LRESULT = ctypes.c_ssize_t
        UINT_PTR = ctypes.c_size_t
        PROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT,
                                  wintypes.WPARAM, wintypes.LPARAM, UINT_PTR, UINT_PTR)
        self.controls.SetWindowSubclass.argtypes = [wintypes.HWND, PROC, UINT_PTR, UINT_PTR]
        self.controls.SetWindowSubclass.restype = wintypes.BOOL
        self.controls.RemoveWindowSubclass.argtypes = [wintypes.HWND, PROC, UINT_PTR]
        self.controls.RemoveWindowSubclass.restype = wintypes.BOOL
        self.controls.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        self.controls.DefSubclassProc.restype = LRESULT
        self.shell.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
        self.shell.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
        self.shell.DragQueryFileW.restype = wintypes.UINT
        self.shell.DragFinish.argtypes = [wintypes.HANDLE]
        @PROC
        def dispatch(hwnd, message, wparam, lparam, ident, data):
            if message == 0x233:  # WM_DROPFILES
                try:
                    count = self.shell.DragQueryFileW(wparam, 0xFFFFFFFF, None, 0)
                    if count > 100000:raise ValueError('Trop de fichiers déposés.')
                    paths = []
                    for index in range(count):
                        length = self.shell.DragQueryFileW(wparam, index, None, 0)
                        buffer = ctypes.create_unicode_buffer(length + 1)
                        self.shell.DragQueryFileW(wparam, index, buffer, length + 1)
                        paths.append(buffer.value)
                    # This callback can run while _tkinter has released its GIL
                    # state inside Windows dispatch. Never call Tk from here.
                    self.pending.put(('drop', paths))
                except Exception:
                    self.pending.put(('error', sys.exc_info()))
                finally:
                    self.shell.DragFinish(wparam)
                return 0
            if message == 0x82:  # WM_NCDESTROY
                self.shell.DragAcceptFiles(hwnd, False)
                self.controls.RemoveWindowSubclass(hwnd, self.callback, 1)
                self.windows.discard(hwnd)
            return self.controls.DefSubclassProc(hwnd, message, wparam, lparam)
        self.callback = dispatch
        try:
            for widget in (self.app, self.app.tree, self.app.folders):
                hwnd = widget.winfo_id()
                if not self.controls.SetWindowSubclass(hwnd, self.callback, 1, 0):
                    raise ctypes.WinError(ctypes.get_last_error())
                self.windows.add(hwnd)
                self.shell.DragAcceptFiles(hwnd, True)
        except Exception:
            for hwnd in tuple(self.windows):
                self.shell.DragAcceptFiles(hwnd, False)
                self.controls.RemoveWindowSubclass(hwnd, self.callback, 1)
            self.windows.clear()
            raise


def install(app):
    app.file_drop = TagStudioDrop(app)
    for widget in app.tree.master.master.winfo_children():
        try:
            if widget.cget('text').startswith('  FICHIERS AUDIO'):
                widget.configure(text='  FICHIERS AUDIO • Dépose ici tes fichiers ou dossiers audio')
        except Exception:
            pass
