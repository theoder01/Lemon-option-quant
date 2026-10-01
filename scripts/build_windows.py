# Copyright © 2026 Bo Hu. All rights reserved.
"""Rebuild the local, windowed onedir application with a read-only DB snapshot."""
from contextlib import closing
from pathlib import Path
import os
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != 'win32':
        raise SystemExit('This build script targets Windows only.')
    source = ROOT / 'data' / 'options.db'
    if not source.is_file():
        raise SystemExit(f'Missing historical database: {source}')
    stage = ROOT / 'build' / 'packaging'
    stage.mkdir(parents=True, exist_ok=True)
    # SQLite backup includes committed WAL data without changing the source.
    with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as original:
        with closing(sqlite3.connect(stage / 'options.db')) as snapshot:
            original.backup(snapshot)
    env = dict(os.environ, PYINSTALLER_CONFIG_DIR=str(ROOT / 'build' / 'pyinstaller-cache'))
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm',
        '--workpath', str(ROOT / 'build' / 'pyinstaller'),
        '--distpath', str(ROOT / 'dist'), str(ROOT / 'LemonOptionQuant.spec'),
    ], cwd=ROOT, env=env, check=True)
    print(ROOT / 'dist' / 'LemonOptionQuant' / 'LemonOptionQuant.exe')


if __name__ == '__main__':
    main()
