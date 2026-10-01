# Copyright © 2026 Bo Hu. All rights reserved.
"""Tk branding using shipped assets and the shared runtime-path resolver."""
import sys
import tkinter as tk

from option_quant.runtime_paths import resource_root


HEADER_SIZES = (32, 40, 48, 64, 80, 96, 128)


def apply_branding(root, requested_size):
    assets = resource_root() / 'assets' / 'branding'
    size = min(HEADER_SIZES, key=lambda candidate: abs(candidate - requested_size))
    header = tk.PhotoImage(master=root, data=(assets / f'logo-{size}.png').read_bytes(), format='png')
    if sys.platform == 'win32':
        # Default applies to this window and later Tk toplevels (e.g. the calendar).
        root.iconbitmap(default=str(assets / 'lemon_option_quant.ico'))
    else:
        root._brand_window_icon = tk.PhotoImage(master=root, data=(assets / 'logo-256.png').read_bytes(), format='png')
        root.iconphoto(True, root._brand_window_icon)
    return header
