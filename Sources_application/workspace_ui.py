"""Asynchronous library workspace. Legacy pages and music encoders are preserved."""
import json
import os
from pathlib import Path
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from reliability import BackupStore, Journal, Cancelled, atomic_json, diagnose_rbsync


def bounded_view(value, budget=None):
    """Bound rendering work; complete reports remain exportable."""
    budget = [2000] if budget is None else budget
    budget[0] -= 1
    if budget[0] < 0:
        return 'Suite disponible dans le rapport complet'
    if isinstance(value, dict):
        return {str(k): bounded_view(v, budget) for k, v in list(value.items())[:80]}
    if isinstance(value, (list, tuple)):
        items = [bounded_view(v, budget) for v in value[:200]]
        return items if len(value) <= 200 else {'total': len(value), 'premiers_elements': items, 'note': 'Affichage limité ; exporter le rapport complet pour tous les éléments.'}
    if isinstance(value, str) and len(value) > 6000:
        return value[:6000] + '\n[Texte complet disponible dans le rapport exportable]'
    return value


class Workspace:
    def __init__(self, app):
        self.app = app
        self.home = Path(os.getenv('LOCALAPPDATA', str(Path.home()))) / 'LBR-DJ-Library-Manager-Candidates' / 'workspace'
        self.config_path = self.home / 'config.json'
        try:
            self.config = json.loads(self.config_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            self.config = {}
        self.roots = list(self.config.get('roots', []))
        self.store = BackupStore(self.config.get('backups', str(self.home / 'backups')))
        self.journal = Journal(self.home / 'tasks.sqlite')
        self.app.bind('<Destroy>', self.root_destroyed, add='+')
        self.cancel = threading.Event()
        self.current_task = None
        self.task_cancelled = False
        self.task_failure = None
        self.pending_snapshots = []
        self.analysis_cache = {}
        self.catalogue_instance = None
        self.window = None
        self.plan = None
        self.last_report = {}
        self.task_total = self.task_done = 0
        self.app.hub.listeners.append(self.task_changed)
        self.app.hub.finalizers.append(self.finalize)
        from manager_core import PALETTES
        for mode, colors in PALETTES.items():
            self.app.style.configure(mode+'.TNotebook', background=colors['bg'], bordercolor=colors['border'])
            self.app.style.configure(mode+'.TNotebook.Tab', background=colors['input'], foreground=colors['muted'], padding=(10, 7))
            self.app.style.map(mode+'.TNotebook.Tab', background=[('selected', colors['blue']), ('active', colors['hover'])], foreground=[('selected', 'white'), ('active', colors['text'])])
        self.app._style_names.add('TNotebook')
        # Optional workspace: safety services stay active without opening a window.

    def first_use(self):
        self.open()
        self.wizard()

    def root_destroyed(self, event):
        if event.widget is self.app:
            self.journal.close()

    @property
    def catalogue(self):
        if self.catalogue_instance is None:
            from library_services import Catalogue
            self.catalogue_instance = Catalogue(self.home / 'catalogue.sqlite')
        return self.catalogue_instance

    def task_changed(self, busy, owner, title):
        if busy:
            self.cancel.clear()
            self.task_cancelled = False
            self.task_failure = None
            self.task_done = self.task_total = 0
            self.current_task = self.journal.start(owner, title)
        elif self.current_task:
            state = 'failed' if title == 'Erreur' else ('cancelled' if self.task_cancelled else 'completed')
            self.journal.update(self.current_task, state, self.task_done, self.task_total, self.task_failure or title)
            self.current_task = None

    def finalize(self, failure):
        # Hash potentially large databases on the worker, never the UI thread.
        self.task_failure = failure
        snapshots, self.pending_snapshots = self.pending_snapshots, []
        for identifier in snapshots:
            self.store.mark(identifier, 'failed' if failure else 'finished')

    def checkpoint(self):
        if self.cancel.is_set():
            self.task_cancelled = True
            raise Cancelled('Annulation demandée ; arrêt au prochain point sûr')

    def progress(self, done, total):
        self.task_done, self.task_total = done, total
        if self.current_task:
            self.journal.update(self.current_task, done=done, total=total)
        self.app.hub.post(self.set_status, f'{done} / {total}' if total else f'{done} éléments analysés')

    def set_status(self, text):
        if self.window and self.window.winfo_exists():
            self.status.set(text)
            if self.task_total:
                self.bar.configure(mode='determinate', maximum=self.task_total, value=self.task_done)

    def submit(self, title, work, callback=None):
        if self.app.hub.busy:
            messagebox.showinfo('Tâche en cours', 'Attends la fin de la tâche actuelle.', parent=self.app)
            return
        def job():
            try:
                result = work()
                if result is not None:
                    self.last_report = result
                if callback:
                    self.app.hub.post(callback, result)
                self.app.hub.post(self.set_status, 'Terminé : ' + title)
            except Cancelled:
                self.app.hub.post(self.set_status, 'Annulé au point sûr')
        self.app.hub.run('Bibliothèque', title, job)

    def save_config(self):
        self.config.update(roots=self.roots, backups=str(self.store.root))
        atomic_json(self.config_path, self.config)

    def choose_root(self):
        if self.app.hub.busy: return
        folder = filedialog.askdirectory(parent=self.window, title='Autoriser un dossier musical')
        if folder and folder not in self.roots:
            self.roots.append(str(Path(folder).resolve()))
            self.save_config()
            self.root_text.set('\n'.join(self.roots))

    def choose_backup(self):
        if self.app.hub.busy: return
        folder = filedialog.askdirectory(parent=self.window, title='Emplacement des sauvegardes')
        if folder:
            self.store = BackupStore(folder)
            self.save_config()
            self.set_status('Sauvegardes : ' + folder)

    def show_report(self, value, title='Rapport'):
        win = tk.Toplevel(self.app)
        win.title(title)
        win.geometry('900x600')
        text = tk.Text(win, wrap='none')
        text.pack(fill='both', expand=True)
        self.last_report = value
        text.insert('1.0', json.dumps(bounded_view(value), ensure_ascii=False, indent=2, default=str))
        text.configure(state='disabled')
        self.app._open_windows.add(win)
        self.app.theme_scope(win)
        return win

    def confirm_plan(self, plan):
        """Runs entirely on the UI thread via TaskHub.ui for legacy workers."""
        win = self.show_report(plan, 'Prévisualisation — avant / après')
        accepted = tk.BooleanVar(win, False)
        def finish(value):
            accepted.set(value)
            win.destroy()
        actions = ttk.Frame(win)
        actions.pack(fill='x')
        ttk.Button(actions, text='Annuler', command=lambda: finish(False)).pack(side='right', padx=8, pady=8)
        ttk.Button(actions, text='Confirmer ces modifications', command=lambda: finish(True)).pack(side='right', padx=8)
        win.protocol('WM_DELETE_WINDOW', lambda: finish(False))
        win.transient(self.app)
        win.grab_set()
        self.app.wait_window(win)
        return accepted.get()

    def open(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return
        w = self.window = tk.Toplevel(self.app)
        w.title('Bibliothèque et sécurité — LBR')
        w.geometry('1100x760')
        self.app._open_windows.add(w)
        self.status = tk.StringVar(w, 'Prêt — les analyses sont en lecture seule')
        footer = ttk.Frame(w)
        footer.pack(side='bottom', fill='x', padx=12, pady=10)
        ttk.Label(footer, textvariable=self.status).pack(side='left')
        self.bar = ttk.Progressbar(footer, length=150)
        self.bar.pack(side='right')
        ttk.Button(footer, text='Annuler au point sûr', command=self.cancel.set).pack(side='right', padx=8)
        self.advanced_button = ttk.Button(footer, text='Afficher les outils avancés', command=self.toggle_advanced)
        self.advanced_button.pack(side='right', padx=8)
        notebook = self.notebook = ttk.Notebook(w)
        notebook.pack(fill='both', expand=True, padx=12, pady=12)
        self.tabs = {}
        from release_info import STAGE
        names = ['Accueil', 'Dossiers', 'Sauvegardes', 'Tâches', 'Diagnostic']
        if STAGE >= 45: names[2:2] = ['Recherche', 'Analyses']
        if STAGE >= 50: names += ['Playlists', 'Tags par lots']
        for name in names:
            frame = ttk.Frame(notebook, padding=14)
            notebook.add(frame, text=name)
            self.tabs[name] = frame
        self.build_home()
        self.build_roots()
        if STAGE >= 45:
            self.build_search()
            self.build_analyses()
        self.build_backups()
        self.build_tasks()
        self.build_diagnostic()
        if STAGE >= 50:
            self.build_playlists()
            self.build_batch()
        self.advanced_visible = True
        self.toggle_advanced()
        def close():
            # The worker belongs to the main app, not this secondary window.
            w.destroy()
            self.window = None
        w.protocol('WM_DELETE_WINDOW', close)
        self.app.theme_scope(w)

    def toggle_advanced(self):
        self.advanced_visible = not self.advanced_visible
        for name, frame in self.tabs.items():
            if name in ('Accueil', 'Dossiers', 'Sauvegardes', 'Tâches'):
                continue
            if self.advanced_visible:
                self.notebook.add(frame)
            else:
                self.notebook.hide(frame)
        self.advanced_button.configure(text='Masquer les outils avancés' if self.advanced_visible else 'Afficher les outils avancés')

    def button(self, parent, text, command):
        b = ttk.Button(parent, text=text, command=command)
        b.pack(anchor='w', pady=5)
        return b

    def build_home(self):
        f = self.tabs['Accueil']
        ttk.Label(f, text='Bibliothèque et sauvegardes', style='Header.TLabel').pack(anchor='w')
        ttk.Label(f, text='Espace facultatif : choisis tes dossiers, consulte tes sauvegardes et suis les opérations.\nLes protections restent actives lorsque cette fenêtre est fermée.', wraplength=900, justify='left').pack(anchor='w', pady=(8, 0))
        self.summary = tk.StringVar(f, 'Statistiques non chargées')
        ttk.Label(f, textvariable=self.summary, wraplength=950, justify='left').pack(anchor='w', pady=15)
        def done(report):
            self.summary.set(f"{report['music']['tracks']} titres · {report['music']['artists']} artistes · {report['music']['genres']} genres\nDernière sauvegarde : {report['backup']}\nTâches récentes : {len(report['tasks'])}\nChemins manquants : {report['analyses'].get('missing', 'analyse à lancer')} · Doublons : {report['analyses'].get('duplicates', 'analyse à lancer')}")
            modules = ' · '.join(self.app.engines[k][1]+(' : ouvert' if k in self.app.apps else ' : fermé') for k in self.app.engines)
            recent = '\n'.join(r['title']+' — '+r['state'] for r in report['tasks'] if r['title'] != 'Statistiques')
            self.summary.set(self.summary.get()+'\n'+modules+'\nDernières opérations :\n'+recent[:1500])
        def stats():
            backups = self.store.list()
            return {'music': self.catalogue.stats(), 'backup': backups[0]['created'] if backups else 'aucune', 'tasks': self.journal.list(10), 'analyses': dict(self.analysis_cache)}
        from release_info import STAGE
        if STAGE >= 45:
            self.button(f, 'Actualiser les statistiques', lambda: self.submit('Statistiques', stats, done))
        if STAGE >= 50:
            self.button(f, 'Assistant de première utilisation', self.wizard)
        for key in self.app.engines:
            self.button(f, self.app.engines[key][1], lambda k=key: self.app.show_page(k))
        ttk.Label(f, text='WAV : crates Serato compatibles. Hot Cues et Saved Loops WAV non pris en charge.', wraplength=800).pack(anchor='w', pady=12)

    def build_roots(self):
        f = self.tabs['Dossiers']
        self.root_text = tk.StringVar(f, '\n'.join(self.roots))
        ttk.Label(f, text='Dossiers autorisés pour les nouvelles analyses').pack(anchor='w')
        ttk.Label(f, textvariable=self.root_text, wraplength=900).pack(anchor='w', pady=12)
        self.button(f, 'Ajouter un dossier', self.choose_root)
        self.button(f, 'Choisir les sauvegardes', self.choose_backup)
        def index():
            self.submit('Indexation en lecture seule', lambda: self.catalogue.index(self.roots, self.checkpoint, self.progress), lambda r: self.show_report(r))
        from release_info import STAGE
        if STAGE >= 45:
            self.button(f, 'Indexer / actualiser les dossiers autorisés', index)
        self.button(f, 'Retirer les autorisations', self.clear_roots)

    def clear_roots(self):
        if self.app.hub.busy: return
        if messagebox.askyesno('Dossiers autorisés', 'Retirer les autorisations ? Les fichiers musicaux sont conservés.', parent=self.window):
            self.roots.clear()
            self.save_config()
            self.root_text.set('')

    def build_search(self):
        f = self.tabs['Recherche']
        row = ttk.Frame(f)
        row.pack(fill='x')
        self.query = tk.StringVar(f)
        self.bpm_min = tk.StringVar(f)
        self.bpm_max = tk.StringVar(f)
        self.key_filter = tk.StringVar(f)
        for label, var, width in [('Artiste, titre, album, genre, année', self.query, 36), ('BPM min', self.bpm_min, 8), ('BPM max', self.bpm_max, 8), ('Tonalité', self.key_filter, 8)]:
            cell = ttk.Frame(row)
            cell.pack(side='left', padx=4)
            ttk.Label(cell, text=label).pack(anchor='w')
            ttk.Entry(cell, textvariable=var, width=width).pack()
        self.result_tree = ttk.Treeview(f, columns=('artist', 'title', 'genre', 'bpm', 'path'), show='headings', selectmode='extended')
        for field in ('artist', 'title', 'genre', 'bpm', 'path'):
            self.result_tree.heading(field, text={'artist':'Artiste','title':'Titre','genre':'Genre','bpm':'BPM','path':'Chemin'}[field])
            self.result_tree.column(field, width=130 if field != 'path' else 350)
        self.result_tree.pack(fill='both', expand=True, pady=12)
        self.page = 0
        self.results = {}
        actions = ttk.Frame(f)
        actions.pack(fill='x')
        for label, cmd in [('Rechercher', lambda: self.search(0)), ('Précédent', lambda: self.search(max(0, self.page - 1))), ('Suivant', lambda: self.search(self.page + 1))]:
            ttk.Button(actions, text=label, command=cmd).pack(side='left', padx=5)

    def search(self, page):
        q = self.query.get()
        filters = {k: v.get() for k, v in [('bpm_min', self.bpm_min), ('bpm_max', self.bpm_max), ('key', self.key_filter)] if v.get()}
        def done(rows):
            self.page = page
            self.result_tree.delete(*self.result_tree.get_children())
            self.results = {str(n): r for n, r in enumerate(rows)}
            for iid, r in self.results.items():
                self.result_tree.insert('', 'end', iid=iid, values=[r.get(k, '') for k in ('artist', 'title', 'genre', 'bpm', 'path')])
            self.set_status(f'Page {page + 1} · {len(rows)} résultats (100 maximum par page)')
        self.submit('Recherche', lambda: self.catalogue.search(q, filters, page), done)

    def build_analyses(self):
        f = self.tabs['Analyses']
        self.button(f, 'Détecter les doublons — aucune suppression', lambda: self.submit('Doublons', self.duplicates_report, lambda r: self.show_report(r)))
        self.button(f, 'Rechercher les chemins manquants', lambda: self.submit('Chemins manquants', self.path_proposals, lambda r: self.show_report(r)))
        self.button(f, 'Analyser la qualité technique des titres sélectionnés', self.quality)
        self.button(f, 'Réparer un chemin dans un export XML Rekordbox', self.repair)
        ttk.Label(f, text='Le débit ne prouve pas la qualité réelle. Les correspondances probables ne sont pas des doublons établis. La réparation concerne un export XML, sans accès à master.db.', wraplength=850).pack(anchor='w', pady=15)
        self.button(f, 'Exporter le dernier rapport JSON', self.export_report)

    def path_proposals(self):
        from library_services import propose_paths
        missing = self.catalogue.missing(self.roots, self.checkpoint)
        self.analysis_cache['missing'] = len(missing)
        return propose_paths(missing, self.roots, self.checkpoint)

    def duplicates_report(self):
        report = self.catalogue.duplicates(self.roots, self.checkpoint)
        self.analysis_cache['duplicates'] = len(report['exact_sha256']) + len(report['probable'])
        return report

    def selected_paths(self):
        return [self.results[i]['path'] for i in self.result_tree.selection()]

    def quality(self):
        from library_services import audio_info, authorized
        paths = self.selected_paths()
        if not paths:
            messagebox.showinfo('Analyse', 'Sélectionne des titres dans Recherche.', parent=self.window)
            return
        def work():
            result = []
            for n, p in enumerate(paths, 1):
                self.checkpoint()
                result.append(audio_info(authorized(p, self.roots)))
                self.progress(n, len(paths))
            return result
        self.submit('Qualité technique', work, lambda r: self.show_report(r))

    def repair(self):
        from library_services import repair_xml
        source = filedialog.askopenfilename(parent=self.window, title='Export XML Rekordbox', filetypes=[('XML', '*.xml')])
        if not source:
            return
        old = simpledialog.askstring('Ancien chemin', 'Chemin manquant exact dans le XML :', parent=self.window)
        if not old:
            return
        new = filedialog.askopenfilename(parent=self.window, title='Choisir la nouvelle correspondance')
        if not new:
            return
        output = filedialog.asksaveasfilename(parent=self.window, title='Enregistrer un XML réparé', defaultextension='.xml')
        if not output:
            return
        plan = {'module': 'Chemins XML', 'changes': [{'before': old, 'after': new}], 'output': output}
        if self.confirm_plan(plan):
            self.submit('Réparation XML', lambda: repair_xml(source, {old: new}, self.roots, self.store, output), lambda r: self.show_report(r))

    def build_backups(self):
        f = self.tabs['Sauvegardes']
        self.backup_tree = ttk.Treeview(f, columns=('date', 'label', 'files'), show='headings')
        for k in ('date', 'label', 'files'):
            self.backup_tree.heading(k, text=k)
        self.backup_tree.pack(fill='both', expand=True)
        self.button(f, 'Actualiser', self.refresh_backups)
        self.button(f, 'Vérifier l’intégrité', lambda: self.backup_action(False))
        self.button(f, 'Restaurer les fichiers choisis', lambda: self.backup_action(True))

    def refresh_backups(self):
        def done(rows):
            self.backup_tree.delete(*self.backup_tree.get_children())
            for r in rows:
                self.backup_tree.insert('', 'end', iid=r['id'], values=(r['created'], r['label'], len(r['files'])))
        self.submit('Lister les sauvegardes', self.store.list, done)

    def backup_action(self, restore):
        ids = self.backup_tree.selection()
        if not ids:
            return
        identifier = ids[0]
        if not restore:
            self.submit('Vérifier une sauvegarde', lambda: self.store.verify(identifier), lambda r: self.show_report(r))
            return
        def choose(data):
            win = tk.Toplevel(self.app)
            win.title('Choisir les fichiers à restaurer')
            tree = ttk.Treeview(win, columns=('path',), show='headings', selectmode='extended', height=16)
            tree.heading('path', text='Chemin original')
            tree.column('path', width=800)
            tree.pack(fill='both', expand=True)
            for n, item in enumerate(data['files']):
                tree.insert('', 'end', iid=str(n), values=(item['path'],))
            def apply():
                selected = [data['files'][int(i)]['path'] for i in tree.selection()]
                if selected and messagebox.askyesno('Restauration', f'Restaurer {len(selected)} fichier(s) après vérification des conflits ?', parent=win):
                    win.destroy()
                    self.submit('Restauration sélective', lambda: {'restored': self.store.restore(identifier, selected, self.checkpoint)}, lambda r: self.show_report(r))
            ttk.Button(win, text='Restaurer la sélection', command=apply).pack(pady=10)
            self.app._open_windows.add(win)
            self.app.theme_scope(win)
        self.submit('Lire la sauvegarde', lambda: self.store.verify(identifier), choose)

    def build_tasks(self):
        f = self.tabs['Tâches']
        self.task_tree = ttk.Treeview(f, columns=('owner', 'title', 'state', 'progress'), show='headings')
        for k in ('owner', 'title', 'state', 'progress'):
            self.task_tree.heading(k, text=k)
        self.task_tree.pack(fill='both', expand=True)
        def refresh():
            self.task_tree.delete(*self.task_tree.get_children())
            for r in self.journal.list():
                self.task_tree.insert('', 'end', values=(r['owner'], r['title'], r['state'], f"{r['done']}/{r['total']}"))
            for owner, title, _, _, _ in self.app.hub.deferred.values():
                self.task_tree.insert('', 'end', values=(owner, title, 'pending', '—'))
        self.button(f, 'Actualiser les tâches et interruptions', refresh)
        def export():
            path = filedialog.asksaveasfilename(parent=self.window, defaultextension='.json')
            if path:
                self.submit('Exporter les tâches', lambda: self.journal.export(path))
        self.button(f, 'Exporter l’historique JSON', export)
        ttk.Label(f, text='Annulation coopérative : les écritures en cours se terminent. Un processus rbsync externe ne peut pas être interrompu sans risque.', wraplength=800).pack(anchor='w', pady=10)

    def build_diagnostic(self):
        f = self.tabs['Diagnostic']
        def run():
            import sys
            base = Path(os.getenv('LOCALAPPDATA', str(Path.home()))) / 'rbsync'
            candidates = [sys.executable, base / 'venv313/Scripts/python.exe', base / 'venv/Scripts/python.exe']
            self.submit('Diagnostic rbsync en lecture seule', lambda: diagnose_rbsync(candidates), lambda r: self.show_report(r))
        self.button(f, 'Vérifier Python, rbsync et --help', run)
        ttk.Label(f, text='Ce diagnostic n’installe rien. Un environnement nommé venv313 ne garantit pas Python 3.13 : la version réelle est vérifiée.', wraplength=800).pack(anchor='w', pady=12)
        self.button(f, 'Exporter le diagnostic', self.export_report)

    def build_playlists(self):
        f = self.tabs['Playlists']
        self.rule_mode = tk.StringVar(f, 'AND')
        ttk.Combobox(f, textvariable=self.rule_mode, values=['AND', 'OR'], state='readonly').pack(anchor='w')
        self.rule_rows = []
        for _ in range(3):
            row = ttk.Frame(f)
            row.pack(fill='x', pady=8)
            field, op, value = tk.StringVar(row, 'genre'), tk.StringVar(row, '='), tk.StringVar(row)
            for var, choices in [(field, ['genre', 'year', 'bpm', 'key', 'artist', 'album', 'format']), (op, ['=', '!=', 'contains', '>=', '<='])]:
                ttk.Combobox(row, textvariable=var, values=choices, state='readonly', width=16).pack(side='left', padx=4)
            ttk.Entry(row, textvariable=value, width=35).pack(side='left', padx=4)
            self.rule_rows.append((field, op, value))
        self.button(f, 'Prévisualiser les correspondances', lambda: self.submit('Aperçu playlist', lambda: self.catalogue.search(rules=self.rules(), page_size=500), lambda r: self.show_report(r)))
        self.button(f, 'Exporter / actualiser une playlist M3U8', self.playlist_export)
        self.button(f, 'Enregistrer ces règles', self.save_rules)
        self.button(f, 'Charger des règles enregistrées', self.load_rules)

    def rules(self):
        rules = []
        for field, op, value in self.rule_rows:
            if value.get():
                v = float(value.get()) if field.get() in ('year', 'bpm') else value.get()
                rules.append({'field': field.get(), 'op': op.get(), 'value': v})
        if not rules:
            raise ValueError('Saisir au moins une règle')
        return {'mode': self.rule_mode.get(), 'rules': rules}

    def save_rules(self):
        path = filedialog.asksaveasfilename(parent=self.window, defaultextension='.json')
        if path:
            atomic_json(path, self.rules())

    def load_rules(self):
        from library_services import compile_rules
        path = filedialog.askopenfilename(parent=self.window, filetypes=[('JSON', '*.json')])
        if not path:
            return
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        compile_rules(data)
        rows = data.get('rules', [])
        if len(rows) > 3 or any('field' not in row for row in rows):
            self.show_report(data, 'Règles imbriquées — disponibles dans le moteur, éditeur limité à trois conditions')
            return
        self.rule_mode.set(data.get('mode', 'AND'))
        for variables, rule in zip(self.rule_rows, rows + [{}] * (3 - len(rows))):
            variables[0].set(rule.get('field', 'genre'))
            variables[1].set(rule.get('op', '='))
            variables[2].set(str(rule.get('value', '')))

    def playlist_export(self):
        from library_services import export_playlist
        rules = self.rules()
        path = filedialog.asksaveasfilename(parent=self.window, defaultextension='.m3u8')
        if path and self.confirm_plan({'rules': rules, 'destination': path, 'action': 'Créer ou remplacer la playlist après sauvegarde'}):
            self.submit('Playlist intelligente', lambda: export_playlist(self.catalogue, rules, path, self.roots, self.store, self.checkpoint), lambda r: self.show_report(r))

    def build_batch(self):
        f = self.tabs['Tags par lots']
        ttk.Label(f, text='Sélectionne les titres dans Recherche, puis prépare une transformation.').pack(anchor='w')
        self.batch_vars = {}
        for label, key, values in [('Champ', 'field', ['title', 'artist', 'album', 'genre', 'date', 'comment', 'bpm', 'key', 'track']), ('Action', 'action', ['set', 'replace', 'regex', 'normalize', 'filename']), ('Valeur', 'value', None), ('Rechercher', 'search', None), ('Remplacer par', 'replacement', None), ('Modèle de nom, ex. {artist} - {title}', 'pattern', None)]:
            row = ttk.Frame(f)
            row.pack(fill='x', pady=5)
            ttk.Label(row, text=label, width=38).pack(side='left')
            var = self.batch_vars[key] = tk.StringVar(row, values[0] if values else '')
            if values:
                ttk.Combobox(row, textvariable=var, values=values, state='readonly').pack(side='left')
            else:
                ttk.Entry(row, textvariable=var, width=55).pack(side='left')
        self.button(f, 'Préparer l’aperçu avant / après', self.prepare_batch)
        self.button(f, 'Appliquer l’aperçu confirmé', self.commit_batch)
        self.button(f, 'Enregistrer le modèle', self.save_template)
        self.button(f, 'Charger un modèle', self.load_template)
        ttk.Label(f, text='Pochettes par lots : utiliser Tag Studio → sélection multiple → Ajouter / retirer une pochette. Les sauvegardes communes protègent chaque écriture.', wraplength=850).pack(anchor='w', pady=12)

    def prepare_batch(self):
        from library_services import batch_plan
        paths = self.selected_paths()
        transform = {k: v.get() for k, v in self.batch_vars.items()}
        if not paths:
            return messagebox.showinfo('Tags', 'Sélectionne des titres dans Recherche.', parent=self.window)
        def done(plan):
            self.plan = plan
            self.show_report(plan, 'Aperçu des tags')
        self.submit('Préparer les tags', lambda: batch_plan(paths, [transform], self.roots, self.checkpoint), done)

    def commit_batch(self):
        from library_services import apply_batch
        plan = self.plan
        if plan and self.confirm_plan(plan):
            self.plan = None
            self.submit('Appliquer les tags', lambda: {'backup': apply_batch(plan, self.roots, self.store, self.checkpoint, self.progress)}, lambda r: self.show_report(r))

    def save_template(self):
        path = filedialog.asksaveasfilename(parent=self.window, defaultextension='.json')
        if path:
            atomic_json(path, {k: v.get() for k, v in self.batch_vars.items()})

    def load_template(self):
        path = filedialog.askopenfilename(parent=self.window, filetypes=[('JSON', '*.json')])
        if path:
            data = json.loads(Path(path).read_text(encoding='utf-8'))
            for k, var in self.batch_vars.items():
                if k in data:
                    var.set(data[k])

    def export_report(self):
        path = filedialog.asksaveasfilename(parent=self.window, defaultextension='.json')
        if path:
            report = self.last_report
            self.submit('Exporter un rapport', lambda: atomic_json(path, report))

    def wizard(self):
        win = tk.Toplevel(self.app)
        win.title('Première utilisation — lecture seule')
        win.geometry('740x420')
        self.app._open_windows.add(win)
        steps = [
            ('Bienvenue', 'Quatre outils historiques et un espace commun. Aucune modification musicale automatique.'),
            ('Environnement', 'Vérifier la version réelle de Python et conserver les rapports de validation Windows.'),
            ('Dépendances', 'Lancer le diagnostic en lecture seule depuis l’onglet Diagnostic.'),
            ('Dossiers autorisés', 'Choisir uniquement les dossiers que les nouvelles analyses peuvent lire.'),
            ('Sauvegardes', 'Choisir un emplacement avec assez d’espace pour les copies des fichiers modifiés.'),
            ('Première indexation', 'Le bouton Indexer du volet Dossiers lit les métadonnées et écrit uniquement l’index indépendant.'),
            ('Prévisualisations', 'Un aperçu présente avant / après. Un fichier changé depuis sa préparation bloque l’écriture.'),
            ('Tableau de bord', 'Les statistiques se chargent à la demande et les traitements passent par le coordinateur commun.')]
        index = [0]
        title = tk.StringVar(win)
        description = tk.StringVar(win)
        ttk.Label(win, textvariable=title, style='Header.TLabel').pack(anchor='w', padx=24, pady=20)
        ttk.Label(win, textvariable=description, wraplength=670).pack(anchor='w', padx=24, pady=12)
        actions = ttk.Frame(win)
        actions.pack(fill='x', padx=24)
        def render():
            title.set(f'{index[0] + 1}/8 — {steps[index[0]][0]}')
            description.set(steps[index[0]][1])
            for child in actions.winfo_children():
                child.destroy()
            if index[0] == 1:
                import sys, platform
                self.button(actions, 'Afficher l’environnement', lambda: self.show_report({'Python': sys.version, 'Système': platform.platform()}))
            if index[0] == 2:
                import sys
                self.button(actions, 'Diagnostiquer sans installer', lambda: self.submit('Diagnostic initial', lambda: diagnose_rbsync([sys.executable]), lambda r: self.show_report(r)))
            if index[0] == 5:
                self.button(actions, 'Lancer la première indexation en lecture seule', lambda: self.submit('Première indexation', lambda: self.catalogue.index(self.roots, self.checkpoint, self.progress), lambda r: self.show_report(r)))
            if index[0] == 6:
                self.button(actions, 'Voir un exemple sans modification', lambda: self.show_report({'Exemple fictif': {'avant': {'genre': 'Inconnu'}, 'après': {'genre': 'Maloya'}}, 'application': 'Aucune écriture'}))
            if index[0] == 3:
                self.button(actions, 'Choisir un dossier autorisé', self.choose_root)
            if index[0] == 4:
                self.button(actions, 'Choisir les sauvegardes', self.choose_backup)
        def move(delta):
            index[0] = max(0, min(7, index[0] + delta))
            render()
        buttons = ttk.Frame(win)
        buttons.pack(side='bottom', fill='x', padx=24, pady=18)
        ttk.Button(buttons, text='Précédent', command=lambda: move(-1)).pack(side='left')
        ttk.Button(buttons, text='Suivant', command=lambda: move(1)).pack(side='left', padx=8)
        def finish():
            self.config['onboarded'] = True
            self.save_config()
            win.destroy()
        ttk.Button(buttons, text='Terminer', command=finish).pack(side='right')
        render()
        self.app.theme_scope(win)
