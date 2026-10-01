# Copyright © 2026 Bo Hu. All rights reserved.
"""Verify real Tk resource loading and the Windows multi-size icon container."""
from pathlib import Path
import struct
import sys
import tkinter as tk
import unittest
from unittest.mock import patch

from option_quant.gui_branding import apply_branding


ROOT = Path(__file__).resolve().parents[1]


class BrandingTests(unittest.TestCase):
    def test_source_and_frozen_resources_load_in_tk(self):
        root = tk.Tk()
        root.withdraw()
        self.addCleanup(root.destroy)
        for frozen in (False, True):
            with self.subTest(frozen=frozen), \
                    patch.object(sys, 'frozen', frozen, create=True), \
                    patch.object(sys, '_MEIPASS', str(ROOT), create=True):
                with patch.object(root, 'iconbitmap', wraps=root.iconbitmap) as iconbitmap:
                    for size in (32, 48, 64):
                        image = apply_branding(root, size)
                        self.assertEqual((image.width(), image.height()), (size, size))
                    if sys.platform == 'win32':
                        # Windows does not return a file name for a default icon.
                        iconbitmap.assert_called_with(
                            default=str(ROOT / 'assets/branding/lemon_option_quant.ico')
                        )

    def test_ico_contains_all_windows_sizes(self):
        data = (ROOT / 'assets/branding/lemon_option_quant.ico').read_bytes()
        reserved, kind, count = struct.unpack_from('<HHH', data)
        self.assertEqual((reserved, kind), (0, 1))
        sizes = set()
        for index in range(count):
            width, height, _, _, _, _, length, offset = struct.unpack_from(
                '<BBBBHHII', data, 6 + index * 16
            )
            sizes.add((width or 256, height or 256))
            self.assertGreater(length, 0)
            self.assertLessEqual(offset + length, len(data))
        self.assertEqual(sizes, {(s, s) for s in (16, 24, 32, 48, 64, 128, 256)})
