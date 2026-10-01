# Local Windows build (Task 5A)

The GUI entry point is `scripts/launch_put_gui.py`. Build on Windows with Python 3.14 (the locally verified version); run from the repository root:

```powershell
py -3.14 -m venv .venv-build
.\.venv-build\Scripts\python.exe -m pip install -r requirements.txt -r requirements-build.txt
.\.venv-build\Scripts\python.exe scripts/build_windows.py
```

The build script takes a consistent SQLite backup of `data/options.db` through a read-only source connection, then builds `LemonOptionQuant.spec`. PyInstaller produces a windowed, onedir application at:

```text
dist/LemonOptionQuant/LemonOptionQuant.exe
```

Double-click this executable. Keep the **entire** `LemonOptionQuant` folder together when moving or copying it; the EXE alone is not sufficient. Python and Futu OpenD are not needed to launch the packaged analysis GUI. The supplied Lemon + L artwork is embedded as the EXE icon.

## Files and paths

- Bundled historical snapshot: `_internal/data/options.db`, relative to the executable directory. GUI access is read-only. Rebuild to include a fresh snapshot, or use the existing database selection UI to select another local database.
- Portable language preference: `data/gui_preferences.json`, relative to the executable directory. Keep the application in a user-writable folder for preference persistence.
- Source execution still resolves its defaults from the repository's `data` directory, independent of the current working directory.
- `option_quant.runtime_paths` contains the frozen/source distinction. Analytics does not know about PyInstaller.
- Tk/Tcl, Python modules and timezone resources are handled by the standard PyInstaller hooks. No custom hidden imports or collect-all rules are used; the unused `futu` API package is excluded. Fee estimation remains part of the GUI.
- Branding PNGs and the multi-resolution ICO are bundled in `_internal/assets/branding`; see `assets/README.md` for the preserved source and derivative-generation command. Windows Explorer may cache icons: check EXE icon resources before treating a stale Explorer icon as a build failure.

Build dependencies are pinned in `requirements-build.txt`. `build/`, `dist/`, and `.venv-build/` are ignored by Git. The spec and build script are maintained source files. The existing private database ignore rules are unchanged. Build output includes your local database snapshot and is intended for local use.

## Verification and diagnostics

Run the existing suite after changes:

```powershell
$env:PYTHONPATH = "$PWD/src"
python -B -m pytest -q
```

Build diagnostics are printed to the calling terminal. PyInstaller's missing-import report is at `build/pyinstaller/LemonOptionQuant/warn-LemonOptionQuant.txt`; platform-specific and optional dependency entries do not necessarily indicate runtime failures. Verify the actual EXE after rebuilding, including both analysis pages, language switching, historical lookup, calculations, calendar and numeric editing. Packaging does not run or package the data collector.

No installer, signing, updating, telemetry or deployment system is included.

Close the running EXE before rebuilding so Windows can replace the distribution files.
