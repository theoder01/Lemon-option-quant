# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 13, 2026

import ast
from pathlib import Path
import re
import sqlite3
from string import Formatter
import tempfile
import unittest
from unittest.mock import patch

from option_quant.gui_i18n import (
    Translator, canonical_message, error_message, load_language,
    message, save_language,
)
from option_quant.gui_strings import LANGUAGES, STRINGS


class TranslationTests(unittest.TestCase):
    def test_catalog_languages_keys_and_placeholders_match(self):
        for key, translations in STRINGS.items():
            with self.subTest(key=key):
                self.assertRegex(key, r'^[a-z][a-z0-9_]*$')
                self.assertEqual(set(translations), set(LANGUAGES))
                fields = lambda text: {(field, spec, conversion) for _, field, spec, conversion
                                       in Formatter().parse(text) if field is not None}
                self.assertEqual(fields(translations['en']), fields(translations['zh_CN']))
                self.assertFalse(re.search(r'[\u4e00-\u9fff]', translations['en']))

    def test_english_default_fallback_and_nested_messages(self):
        self.assertEqual(Translator().render(message('language')), 'Language')
        self.assertEqual(Translator('unsupported').render(message('language')), 'Language')
        value = message('calculation_failed', error=message('invalid_expiry_format'))
        self.assertIn('YYYY-MM-DD', Translator('zh_CN').render(value))
        self.assertIn('无法计算', Translator('zh_CN').render(value))
        self.assertIn('Unable to calculate', Translator().render(value))
        with patch.dict(STRINGS, {'test_fallback': {'en': 'English fallback'}}):
            self.assertEqual(Translator('zh_CN').render(message('test_fallback')), 'English fallback')
        with self.assertRaises(KeyError):
            Translator().render(message('missing_key'))

    def test_core_messages_translate_only_at_display_boundary(self):
        from option_quant.analytics import put_preview
        tree = ast.parse(Path(put_preview.__file__).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.assertFalse(re.search(r'[\u4e00-\u9fff]', node.value))
            if isinstance(node, ast.Call) and node.args:
                is_note = isinstance(node.func, ast.Attribute) and node.func.attr == 'append'
                is_error = isinstance(node.func, ast.Name) and node.func.id == 'ValueError'
                if (is_note or is_error) and isinstance(node.args[0], ast.Constant):
                    text = node.args[0].value
                    self.assertNotEqual(Translator('zh_CN').render(canonical_message(text)), text)

    def test_known_errors_and_unknown_diagnostics(self):
        translator = Translator('zh_CN')
        for error in [ValueError('Premium per share must be a valid number.'),
                      sqlite3.OperationalError('unable to open database file'),
                      sqlite3.OperationalError('no such table: option_snapshots')]:
            self.assertNotIn(str(error), translator.render(error_message(error)))
        self.assertIn('technical-code-123', translator.render(error_message(RuntimeError('technical-code-123'))))

    def test_preference_round_trip_and_malformed_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'preferences.json'
            self.assertEqual(load_language(path), 'en')
            self.assertTrue(save_language(path, 'zh_CN'))
            self.assertEqual(load_language(path), 'zh_CN')
            self.assertTrue(save_language(path, 'en'))
            self.assertEqual(load_language(path), 'en')
            for text in ['invalid', '[]', 'null', '{"language": []}', '{"language": "de"}']:
                path.write_text(text, encoding='utf-8')
                self.assertEqual(load_language(path), 'en')
            with patch.object(Path, 'write_text', side_effect=PermissionError):
                self.assertFalse(save_language(path, 'zh_CN'))

    def test_gui_uses_resource_keys_and_no_literal_widget_text(self):
        from option_quant import put_gui
        tree = ast.parse(Path(put_gui.__file__).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg in ('text', 'title'):
                        self.assertNotIsInstance(keyword.value, ast.Constant)
                if isinstance(node.func, ast.Name) and node.func.id == 'message':
                    if isinstance(node.args[0], ast.Constant):
                        self.assertIn(node.args[0].value, STRINGS)
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.assertFalse(re.search(r'[\u4e00-\u9fff]', node.value))

    def test_calendar_uses_resources_for_prose(self):
        from option_quant import date_picker
        tree = ast.parse(Path(date_picker.__file__).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg in ('text', 'title'):
                        self.assertNotIsInstance(keyword.value, ast.Constant)
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.assertFalse(re.search(r'[\u4e00-\u9fff]', node.value))
                if node.value.startswith('calendar_'):
                    if node.value != 'calendar_month_':
                        self.assertIn(node.value, STRINGS)
        for month in range(1, 13):
            self.assertIn(f'calendar_month_{month}', STRINGS)


if __name__ == '__main__':
    unittest.main()
