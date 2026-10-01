# Copyright © 2026 Bo Hu. All rights reserved.
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from option_quant import runtime_paths
from option_quant import put_gui


class RuntimePathTests(unittest.TestCase):
    def test_source_paths_ignore_working_directory(self):
        root=Path(runtime_paths.__file__).resolve().parents[2]
        original=Path.cwd()
        with tempfile.TemporaryDirectory() as temp, patch.object(sys,'frozen',False,create=True):
            try:
                os.chdir(temp)
                self.assertEqual(runtime_paths.default_database_path(), root/'data/options.db')
                self.assertEqual(runtime_paths.preference_path(), root/'data/gui_preferences.json')
            finally:
                os.chdir(original)

    def test_frozen_paths_distinguish_resources_and_writable_preferences(self):
        portable=Path(tempfile.gettempdir())/'Relocated App'
        with patch.object(sys,'frozen',True,create=True), \
             patch.object(sys,'_MEIPASS',str(portable/'_internal'),create=True), \
             patch.object(sys,'executable',str(portable/'LemonOptionQuant.exe')):
            self.assertEqual(runtime_paths.default_database_path(),portable/'_internal/data/options.db')
            self.assertEqual(runtime_paths.preference_path(),portable/'data/gui_preferences.json')

    @patch('option_quant.put_gui.PutAnalysisWindow')
    @patch('option_quant.put_gui.create_root')
    def test_default_launch_uses_central_paths(self,root,window):
        put_gui.main()
        window.assert_called_once_with(root.return_value,runtime_paths.default_database_path(),runtime_paths.preference_path())
        root.return_value.mainloop.assert_called_once()

    @patch('option_quant.put_gui.PutAnalysisWindow')
    @patch('option_quant.put_gui.create_root')
    def test_explicit_database_override_is_preserved(self,root,window):
        put_gui.main('custom.db')
        self.assertEqual(window.call_args.args[1],Path('custom.db'))


if __name__=='__main__': unittest.main()
