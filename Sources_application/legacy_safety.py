"""Safety adapters around unchanged reference engines.

No external synchronization is run by this module. Existing user confirmations
remain in the legacy controllers; common previews are added for tag changes.
"""
import functools
from pathlib import Path
from reliability import Conflict, digest


def install(key, module, workspace):
    if getattr(module, '_lbr_safety', False):
        return
    store = workspace.store
    # Resolve dynamically: changing backup settings affects subsequent operations.
    get_store = lambda: workspace.store
    if key == 'MusicGenre':
        original = module.write_tags
        @functools.wraps(original)
        def write(path, genre, year):
            workspace.checkpoint()
            with get_store().protect([path], 'MusicGenre', workspace.checkpoint):
                result = original(path, genre, year)
                actual = module.read_tags(path)
                # The reference reader returns (genre, year).
                if tuple(str(v) for v in actual) != (str(genre), str(year)):
                    raise Conflict('Vérification Genre/Année échouée')
                return result
        module.write_tags = write
        apply = module.App.apply
        @functools.wraps(apply)
        def apply_preview(controller, *args, **kwargs):
            changes = [{'path': r[0], 'before': {'genre': r[1], 'year': r[3]}, 'after': {'genre': r[2], 'year': r[4]}} for r in controller.rows if r[5] == 'À modifier']
            if changes and not workspace.app.hub.ui(workspace.confirm_plan, {'module': key, 'changes': changes, 'skipped': []}):
                return
            return apply(controller, *args, **kwargs)
        module.App.apply = apply_preview
    elif key == 'TagStudio':
        module._lbr_backup_ids = {}
        for name in ('safe_write', 'safe_write_cover'):
            original = getattr(module, name)
            def protect(path, *args, _fn=original, _name=name, **kwargs):
                workspace.checkpoint()
                with get_store().protect([path], 'Tag Studio ' + _name, workspace.checkpoint) as identifier:
                    result = _fn(path, *args, **kwargs)
                module._lbr_backup_ids[str(result)] = identifier
                return result
            setattr(module, name, protect)
        save = module.App.save
        @functools.wraps(save)
        def save_preview(controller, *args, **kwargs):
            changes = []
            for path, after in controller.pending.items():
                before = module.read_tags(path)
                changes.append({'path': path, 'before': {k: before.get(k, '') for k in after}, 'after': after})
            if changes and not workspace.app.hub.ui(workspace.confirm_plan, {'module': key, 'changes': changes, 'skipped': []}):
                return
            return save(controller, *args, **kwargs)
        module.App.save = save_preview
        cover = module.App.apply_cover
        @functools.wraps(cover)
        def cover_preview(controller, selected, data, mime, action):
            import hashlib
            changes = []
            for path in selected:
                before = module.read_cover(path)
                changes.append({'path': path, 'before': {'cover_sha256': hashlib.sha256(before).hexdigest() if before else None},
                                'after': {'action': action, 'mime': mime, 'cover_sha256': hashlib.sha256(data).hexdigest() if data else None}})
            if changes and not workspace.app.hub.ui(workspace.confirm_plan, {'module': key, 'changes': changes, 'skipped': []}):
                return
            return cover(controller, selected, data, mime, action)
        module.App.apply_cover = cover_preview
        def rename(controller):
            import os
            import shutil
            paths = controller.selected()
            if not paths:
                return
            pattern = module.simpledialog.askstring('Renommage', 'Modèle de nom', initialvalue='{artist} - {title}')
            if not pattern:
                return
            plans = []
            for path in paths:
                name = module.rename_pattern({**controller.rows[path], **controller.pending.get(path, {})}, pattern)
                if name:
                    target = str(Path(path).with_name(name + Path(path).suffix))
                    if target != path:
                        plans.append((path, target, digest(path)))
            if len({target for _, target, _ in plans}) != len(plans) or any(Path(target).exists() for _, target, _ in plans):
                raise Conflict('Conflit de nom : aucun renommage effectué')
            if not plans or not workspace.app.hub.ui(workspace.confirm_plan, {'module': key, 'changes': [{'before': src, 'after': dst} for src, dst, _ in plans], 'skipped': []}):
                return
            for src, dst, expected in plans:
                workspace.checkpoint()
                if digest(src) != expected:
                    raise Conflict('Fichier modifié depuis l’aperçu : ' + src)
                identifier = get_store().create([src], 'Renommage', workspace.checkpoint)
                # Exclusive creation prevents replacing a target that appeared
                # after preview. Source deletion only follows verified copying.
                with Path(src).open('rb') as reader, Path(dst).open('xb') as writer:
                    shutil.copyfileobj(reader, writer)
                    writer.flush()
                    os.fsync(writer.fileno())
                shutil.copystat(src, dst)
                if digest(dst) != expected or digest(src) != expected:
                    raise Conflict('Copie de renommage non vérifiée ; original conservé')
                Path(src).unlink()
                get_store().mark(identifier)
                backup = str(get_store()._folder(identifier) / '00000000.bin')
                module._lbr_backup_ids[backup] = identifier
                controller.backups.append((src, backup))
                controller.rows[dst] = controller.rows.pop(src)
                controller.rows[dst].update(file=Path(dst).name, path=dst)
                if src in controller.pending:
                    controller.pending[dst] = controller.pending.pop(src)
            controller.populate()
        module.App.rename = rename
        def undo(controller):
            if not controller.backups:
                return
            if not workspace.app.hub.ui(module.messagebox.askyesno, 'Restauration protégée', f'Restaurer {len(controller.backups)} écriture(s) avec vérification des conflits ?'):
                return
            failed = []
            for path, old_backup in reversed(controller.backups):
                identifier = module._lbr_backup_ids.get(str(old_backup))
                try:
                    if not identifier:
                        raise Conflict('Sauvegarde de session sans manifeste commun : restauration manuelle requise')
                    get_store().restore(identifier, [path], workspace.checkpoint)
                    controller.rows.setdefault(path, {}).update(module.read_tags(path))
                except Exception as exc:
                    failed.append((path, old_backup))
                    controller.logmsg('Restauration refusée : ' + str(exc))
            controller.backups = list(reversed(failed))
            controller.populate()
        module.App.undo = undo
    elif key == 'RekordSync':
        original = module.backup_master_db
        def snapshot():
            workspace.checkpoint()
            if module.rb_running():
                raise Conflict('Fermer Rekordbox avant la sauvegarde')
            db = module.master_db_path()
            paths = [db] + [Path(str(db) + suffix) for suffix in ('-wal', '-shm') if Path(str(db) + suffix).exists()]
            if not db.is_file():
                raise FileNotFoundError(str(db))
            identifier = get_store().create(paths, 'Rekordbox master.db', workspace.checkpoint)
            workspace.pending_snapshots.append(identifier)
            data = get_store().verify(identifier)
            return [str(get_store()._folder(identifier) / row['blob']) for row in data['files']]
        module.backup_master_db = snapshot
        # Ensure the multi-playlist path also takes a mandatory common snapshot.
        original_apply = module.App.apply_all
        @functools.wraps(original_apply)
        def guarded_apply(controller, *args, **kwargs):
            if module.rb_running():
                raise Conflict('Fermer Rekordbox avant la synchronisation')
            snapshot()
            return original_apply(controller, *args, **kwargs)
        module.App.apply_all = guarded_apply
    elif key == 'Serato':
        original = module.inject_serato_markers
        @functools.wraps(original)
        def inject(path, *args, **kwargs):
            workspace.checkpoint()
            # Keep the original explicit WAV rejection before any backup/write.
            if Path(path).suffix.lower() not in ('.mp3', '.aif', '.aiff', '.flac'):
                return original(path, *args, **kwargs)
            with get_store().protect([path], 'Marqueurs Serato', workspace.checkpoint):
                return original(path, *args, **kwargs)
        module.inject_serato_markers = inject
        backup = module.App.make_backup
        @functools.wraps(backup)
        def crates_backup(controller, *args, **kwargs):
            workspace.checkpoint()
            root = Path(controller.serato_path.get()) / 'Subcrates'
            files = [p for p in root.rglob('*') if p.is_file()] if root.exists() else []
            if files:
                identifier = get_store().create(files, 'Crates Serato', workspace.checkpoint)
                workspace.pending_snapshots.append(identifier)
            return backup(controller, *args, **kwargs)
        module.App.make_backup = crates_backup
        def restore(controller):
            # Common workspace supports selective conflict-checked restoration.
            workspace.app.hub.ui(workspace.open)
            workspace.app.hub.ui(module.messagebox.showinfo, 'Restauration protégée', 'Utilise Bibliothèque et sécurité → Sauvegardes pour choisir et vérifier les fichiers à restaurer.')
        module.App.restore_last_backup = restore

    if key == 'RekordSync':
        def rb_preview(controller, method):
            changes, skipped = [], []
            if method == 'delete_selected_target':
                kind, target = controller.selected_rb_target()
                return {'module': key, 'changes': [{'before': {'kind': kind, 'target': target}, 'after': 'Suppression de structure ; retrait éventuel des références non utilisées après confirmation séparée'}], 'skipped': ['Aucun fichier audio supprimé']}
            if method == 'import_collection':
                return {'module': key, 'changes': [{'before': 'Absent de la Collection', 'after': path} for path in controller.missing_files], 'skipped': []}
            for directory, playlist_file, count in controller.generate():
                workspace.checkpoint()
                playlist = controller.playlist_arg(directory.name)
                code, output = controller.cmd(['plan', str(playlist_file), '--playlist', playlist])
                absent = 'there is no playlist called' in output.lower()
                if code and not absent:
                    raise Conflict('Aperçu rbsync impossible : ' + output)
                added, removed = module.parse_plan_titles(output)
                if absent and method == 'apply_all':
                    skipped.append({'playlist': playlist, 'reason': 'Absente, ignorée par ce mode'})
                else:
                    changes.append({'playlist': playlist, 'before': {'removed_references': removed, 'exists': not absent},
                                    'after': {'added_references': added, 'source_tracks': count}, 'detail': output})
            return {'module': key, 'changes': changes, 'skipped': skipped}
        for name in ('sync_one_click', 'apply_all', 'import_collection', 'delete_selected_target'):
            fn = getattr(module.App, name)
            def call(controller, *args, _fn=fn, _name=name, **kwargs):
                plan = rb_preview(controller, _name)
                if not workspace.app.hub.ui(workspace.confirm_plan, plan):
                    return
                return _fn(controller, *args, **kwargs)
            setattr(module.App, name, functools.wraps(fn)(call))
    elif key == 'Serato':
        def serato_preview(controller):
            import os
            changes, skipped = [], []
            markers = module.parse_markers_by_path(controller.xml_path.get())
            for playlist in controller.selected_playlists():
                status, adds, removes = controller.compare_playlist(playlist)
                changes.append({'playlist': playlist.display_path, 'before': {'state': status, 'references_removed': removes},
                                'after': {'references_added': adds, 'tracks': playlist.tracks}})
                for path in playlist.tracks:
                    marker = markers.get(os.path.normcase(os.path.abspath(path)), {})
                    if marker.get('cues') or marker.get('loops'):
                        if Path(path).suffix.lower() not in ('.mp3', '.aif', '.aiff', '.flac'):
                            skipped.append({'path': path, 'reason': 'Marqueurs non pris en charge ; WAV compatible avec les crates'})
                        else:
                            changes.append({'path': path, 'after': marker, 'before': 'Marqueurs existants sauvegardés avant transfert'})
            return {'module': key, 'changes': changes, 'skipped': skipped}
        for name in ('sync_changes', 'force_rewrite', 'run_sync'):
            fn = getattr(module.App, name)
            def call(controller, *args, _fn=fn, **kwargs):
                if not workspace.app.hub.ui(workspace.confirm_plan, serato_preview(controller)):
                    return
                return _fn(controller, *args, **kwargs)
            setattr(module.App, name, functools.wraps(fn)(call))
    module._lbr_safety = True
