# Copyright © 2026 Bo Hu. All rights reserved.
# Run via scripts/build_windows.py, which stages a consistent database snapshot.
from pathlib import Path

ROOT = Path(SPECPATH)
a = Analysis(
    [str(ROOT / 'scripts' / 'launch_put_gui.py')],
    pathex=[str(ROOT / 'src')],
    binaries=[],
    datas=[(str(ROOT / 'build' / 'packaging' / 'options.db'), 'data'),
           (str(ROOT / 'assets' / 'branding'), 'assets/branding')],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=['futu'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='LemonOptionQuant', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False,
    icon=str(ROOT / 'assets' / 'branding' / 'lemon_option_quant.ico'),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='LemonOptionQuant')
