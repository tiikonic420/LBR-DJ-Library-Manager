"""Real Tk integration, synthetic data and isolated configuration."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import wave
from unittest.mock import patch
root = Path(__file__).resolve().parents[1]
stage = int(sys.argv[1]) if len(sys.argv) > 1 else 50
source = root / 'Sources_application'
sys.path[:0] = [str(source), str(source / 'modules')]
temp = tempfile.TemporaryDirectory(prefix='lbr_gui_workspace_')
for key in ('HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA'):
    os.environ[key] = temp.name
import release_info
release_info.STAGE = stage
import rekordsync_v5_0_6 as rb
import rekordbox_serato_v1_4 as se
rb.rbsync_python = lambda: None
se.find_serato_roots = lambda: []
from LBR_DJ_Library_Manager_FINAL import LBRManager
app = LBRManager()
errors, checks = [], []
app.report_callback_exception = lambda *args: errors.append(str(args))
app.report_task_error = lambda *args: errors.append(str(args))
w = app.workspace

def check(name, value):
    assert value, name
    checks.append(name)

def settle():
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        app.update()
        if not app.hub.busy and app.hub.messages.empty() and not app.hub.deferred:
            app.update_idletasks()
            return
        time.sleep(.002)
    raise AssertionError('Task timeout')

try:
    for page in app.nav:
        app.show_page(page)
        settle()
    check('four_legacy_engines_open', len(app.apps) == 4)

    # Wait for the automatic Serato startup scheduled by its Tk page.
    # This prevents it from competing with synthetic Workspace tasks.
    if 'Serato' in app.apps:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            app.update()
            rows = w.journal.list()
            serato_finished = any(
                t['title'] == 'Chargement Serato'
                and t['state'] in ('completed', 'failed', 'cancelled')
                for t in rows
            )
            if serato_finished and not app.hub.busy and app.hub.messages.empty():
                break
            time.sleep(.002)
        else:
            raise AssertionError('Serato startup timeout')

    w.open()
    app.update()
    check('stage_tabs', len(w.tabs) == (5 if stage == 41 else 7 if stage == 45 else 9))
    identities = {key: id(value) for key, value in app.pages.items()}
    for mode in ('clair', 'sombre'):
        app.set_theme(mode)
        app.theme_scope(w.window)
        app.update()
        check('workspace_notebook_'+mode, w.notebook.cget('style') == mode+'.TNotebook' and app.style.lookup(mode+'.TNotebook.Tab', 'background', ('selected',)) == app.colors['blue'])
    check('legacy_pages_reused_with_workspace', identities == {key: id(value) for key, value in app.pages.items()})
    music = Path(temp.name) / 'synthetic_music'
    music.mkdir()
    wav = music / 'LBR - ÉTÉ.wav'
    with wave.open(str(wav), 'wb') as stream:
        stream.setparams((2, 2, 44100, 0, 'NONE', 'none'))
        stream.writeframes(b'\0' * 44100 * 4)
    original = wav.read_bytes()
    w.roots = [str(music)]
    w.save_config()
    check('configured_root_does_not_change_audio', wav.read_bytes() == original)
    w.submit('Synthetic progress', lambda: (w.progress(1, 2), w.progress(2, 2)))
    settle()
    check('durable_completed_task', any(t['state'] == 'completed' and t['done'] == 2 for t in w.journal.list()))
    if stage >= 45:
        w.submit('Index synthetic', lambda: w.catalogue.index(w.roots, w.checkpoint, w.progress))
        settle()
        w.search(0)
        settle()
        check('paginated_search_in_gui', len(w.result_tree.get_children()) == 1)
        w.result_tree.selection_set('0')
        w.quality()
        settle()
        check('quality_report_generated', isinstance(w.last_report, list) and not w.last_report[0]['error'])
    if stage >= 50:
        w.batch_vars['field'].set('title')
        w.batch_vars['action'].set('set')
        w.batch_vars['value'].set('ÉTÉ')
        w.prepare_batch()
        settle()
        check('batch_preview_is_read_only', wav.read_bytes() == original and len(w.plan['changes']) == 1)
        # Only synthetic fixture writes are confirmed by this test.
        w.confirm_plan = lambda plan: True
        w.commit_batch()
        settle()
        import tag_engine
        check('confirmed_batch_reaches_tag_engine', tag_engine.read_tags(str(wav))['title'] == 'ÉTÉ')
        w.wizard()
        app.update()
        check('wizard_opens_without_automatic_music_write', tag_engine.read_tags(str(wav))['title'] == 'ÉTÉ')
    w.refresh_backups()
    settle()
    check('backups_view_readable', w.backup_tree.winfo_exists())
    # A cancellation is cooperative and recorded; it does not kill the worker.
    def cancelled():
        w.cancel.set()
        w.checkpoint()
    w.submit('Synthetic cancellation', cancelled)
    settle()
    check('cancelled_task_recorded', any(t['state'] == 'cancelled' for t in w.journal.list()))
    check('no_callback_or_worker_error', not errors)
    check('safe_close_has_no_busy_worker', not app.hub.busy)
finally:
    if not app.hub.busy:
        app.hub.shutdown()
        app.destroy()
print(json.dumps({'stage': stage, 'passed': len(checks), 'checks': checks, 'errors': errors}, ensure_ascii=False, indent=2))
