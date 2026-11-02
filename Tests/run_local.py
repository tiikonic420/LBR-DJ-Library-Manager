"""Local reproducible validation. Optional --gui starts a local Xvfb on Linux.

Use --vendor-site only for supplied pure-Python deps; native packages installed
on the host keep priority. This runner never installs dependencies.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gui', action='store_true')
    parser.add_argument('--vendor-site', default='')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = args.output or root / 'Results' / 'local'
    out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['LBR_TEST_MODE'] = '1'
    results = []
    xserver = None
    temp = tempfile.TemporaryDirectory(prefix='lbr_validation_')
    for key in ('HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA'):
        env[key] = temp.name
    try:
        if args.gui and sys.platform != 'win32':
            display = 97
            log = (out / 'xvfb.log').open('w')
            xserver = subprocess.Popen(['Xvfb', ':' + str(display), '-screen', '0', '1440x1000x24', '-ac', '-listen', 'tcp', '-nolisten', 'unix', '-nolisten', 'local'], stdout=log, stderr=log)
            for _ in range(100):
                try:
                    with socket.create_connection(('127.0.0.1', 6000 + display), .1):
                        break
                except OSError:
                    time.sleep(.05)
            env['DISPLAY'] = '127.0.0.1:' + str(display)
        jobs = [
            ('safety', root / 'Tests/test_reliability.py', []),
            ('journal_durability', root / 'Tests/test_journal_windows.py', []),
            ('adapters', root / 'Tests/test_adapters.py', []),
            ('library', root / 'Tests/test_library.py', []),
            ('audio_formats', root / 'Tests/test_audio_formats.py', []),
            ('historical_regression', root / 'Performance/test_regression.py', []),
            ('historical_invariants', root / 'Performance2/test_p2.py', []),
            ('capture_guard', root / 'Performance2/test_capture_guard.py', []),
        ]
        if args.gui:
            jobs += [
                ('presentation_cache', root / 'Tests/test_presentation_cache.py', []),
                ('page_focus', root / 'Tests/test_page_focus.py', []),
                ('optional_workspace_drop', root / 'Tests/test_optional_drop.py', []),
                ('historical_gui', root / 'Performance/test_gui.py', []),
                ('historical_gui_p2', root / 'Performance2/test_gui_p2.py', []),
                ('historical_shutdown', root / 'Performance2/test_shutdown.py', [str(root / 'Sources_application')]),
                *[(f'workspace_{stage}', root / 'Tests/test_workspace_gui.py', [str(stage)]) for stage in (41, 45, 50)]
            ]
        for name, script, arguments in jobs:
            code = 'import sys,runpy;vendor=sys.argv.pop(1);sys.path.append(vendor) if vendor else None;target=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_path(target,run_name="__main__")'
            start = time.perf_counter()
            with (out / (name + '.log')).open('w') as stream:
                try:
                    cp = subprocess.run([sys.executable, '-c', code, args.vendor_site, str(script), *arguments], env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=240)
                    status = cp.returncode
                except subprocess.TimeoutExpired:
                    status = 124
                    stream.write('\nTIMEOUT: suite failed, not a pass.\n')
            results.append({'suite': name, 'exit_code': status, 'seconds': time.perf_counter() - start})
            print(name, status, flush=True)
            (out / 'summary.json').write_text(json.dumps(results, indent=2))
    finally:
        if xserver:
            xserver.terminate()
            xserver.wait(timeout=10)
        temp.cleanup()
    return int(any(row['exit_code'] for row in results))


if __name__ == '__main__':
    raise SystemExit(main())
