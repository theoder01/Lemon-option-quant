# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 13, 2026

from datetime import date
from pathlib import Path
import tkinter as tk
import unittest
from unittest.mock import patch

from option_quant.gui_strings import LANGUAGES
from option_quant.put_gui import PutAnalysisWindow
from test_put_preview import NOW
from test_put_iv_preview import iv_history


class InputUXTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.window = PutAnalysisWindow(self.root, Path('missing-input-ux-test.db'))
        self.addCleanup(self.root.destroy)
        self.root.update()

    def language(self, code):
        self.window.language.set(LANGUAGES[code])
        self.window.change_language()
        self.root.update()

    def numeric_fields(self):
        for page, tab in [(self.window, self.window.new_page),
                          (self.window.existing_page, self.window.existing_page)]:
            self.window.notebook.select(tab)
            self.root.update()
            for key, entry in page.numeric_entries.items():
                yield f'{type(page).__name__}.{key}', entry

    def focus(self, widget):
        widget.focus_force()
        self.root.update()

    def fill(self):
        self.window.premium.set('2')
        self.window.strike.set('90')
        self.window.spot.set('100')
        self.window.expiry.set('2026-10-28')

    def test_backspace_delete_select_all_and_typing_for_every_numeric_field(self):
        for language in LANGUAGES:
            self.language(language)
            for key, entry in self.numeric_fields():
                with self.subTest(language=language, field=key):
                    self.assertEqual(entry['validate'], 'none')
                    self.focus(entry)
                    entry.delete(0, 'end')
                    entry.insert(0, '12.5')
                    entry.icursor('end')
                    for _ in range(4):
                        entry.event_generate('<BackSpace>')
                    self.assertEqual(entry.get(), '')
                    for keysym in ['1', '2', 'period', '5']:
                        entry.event_generate('<KeyPress>', keysym=keysym)
                    self.assertEqual(entry.get(), '12.5')
                    entry.icursor(0)
                    entry.event_generate('<Delete>')
                    self.assertEqual(entry.get(), '2.5')
                    for sequence, deletion in [('<Control-a>', '<Delete>'), ('<Control-A>', '<BackSpace>')]:
                        entry.delete(0, 'end')
                        entry.insert(0, '12.5')
                        entry.event_generate(sequence)
                        self.assertTrue(entry.selection_present())
                        entry.event_generate(deletion)
                        self.assertEqual(entry.get(), '')
                    # Intermediate signs, decimal points and arbitrary text are
                    # editable; financial validation does not run on keystrokes.
                    for value in ['-', '.', '1.', 'invalid']:
                        entry.delete(0, 'end')
                        entry.insert(0, value)
                        self.assertEqual(entry.get(), value)

    def test_paste_replaces_selection_in_every_numeric_field(self):
        try:
            previous_clipboard = self.root.clipboard_get()
        except tk.TclError:
            previous_clipboard = None
        try:
            for language in LANGUAGES:
                self.language(language)
                for key, entry in self.numeric_fields():
                    with self.subTest(language=language, field=key):
                        self.focus(entry)
                        entry.delete(0, 'end')
                        entry.insert(0, '999')
                        entry.event_generate('<Control-a>')
                        self.root.clipboard_clear()
                        self.root.clipboard_append('123.45')
                        self.root.update()
                        entry.event_generate('<Control-v>')
                        self.assertEqual(entry.get(), '123.45')
                        entry.event_generate('<Control-a>')
                        entry.event_generate('<Control-c>')
                        self.assertEqual(self.root.clipboard_get(), '123.45')
                        entry.event_generate('<Delete>')
                        entry.event_generate('<<Paste>>')
                        self.assertEqual(entry.get(), '123.45')
        finally:
            self.root.clipboard_clear()
            if previous_clipboard is not None:
                self.root.clipboard_append(previous_clipboard)
            self.root.update()

    def test_numeric_editing_when_tk_icu_iterator_cannot_open(self):
        # Reproduce the actual desktop failure, which ordinary event_generate
        # tests miss when ICU happens to work in the test process.
        for name in ('startOfCluster', 'endOfCluster'):
            self.root.tk.call('rename', f'tk::{name}', f'tk::original_{name}')
            self.root.tk.call('proc', f'tk::{name}', 'args',
                              'error {cannot open ICU iterator, errorcode: 2}')
        try:
            for key, entry in self.numeric_fields():
                with self.subTest(field=key):
                    self.focus(entry)
                    entry.delete(0, 'end')
                    entry.insert(0, '1.92')
                    entry.icursor('end')
                    for expected in ('1.9', '1.', '1', ''):
                        entry.event_generate('<BackSpace>')
                        self.assertEqual(entry.get(), expected)
                    entry.event_generate('<BackSpace>')
                    self.assertEqual(entry.get(), '')
                    for deletion in ('<BackSpace>', '<Delete>'):
                        entry.insert(0, '2.35')
                        entry.event_generate('<Control-a>')
                        entry.event_generate(deletion)
                        self.assertEqual(entry.get(), '')
                    entry.insert(0, '1.92')
                    entry.icursor(0)
                    entry.event_generate('<Delete>')
                    self.assertEqual(entry.get(), '.92')
                    entry.event_generate('<Right>')
                    self.assertEqual(entry.index('insert'), 1)
                    entry.event_generate('<Shift-Right>')
                    self.assertEqual(entry.selection_get(), '9')
                    entry.event_generate('<Delete>')
                    self.assertEqual(entry.get(), '.2')
                    entry.event_generate('<KeyPress>', keysym='3')
                    self.assertEqual(entry.get(), '.32')
                    entry.event_generate('<Left>')
                    entry.event_generate('<Shift-Left>')
                    self.assertEqual(entry.selection_get(), '.')
                    entry.event_generate('<BackSpace>')
                    self.assertEqual(entry.get(), '32')
                    entry.icursor('end')
                    entry.event_generate('<Delete>')
                    self.assertEqual(entry.get(), '32')
                    entry.event_generate('<Control-a>')
                    entry.event_generate('<BackSpace>')
                    entry.insert(0, '2.35')
                    self.assertEqual(entry.get(), '2.35')
        finally:
            for name in ('startOfCluster', 'endOfCluster'):
                self.root.tk.call('rename', f'tk::{name}', '')
                self.root.tk.call('rename', f'tk::original_{name}', f'tk::{name}')

    @patch('option_quant.put_gui.now_utc', return_value=NOW)
    @patch('option_quant.put_gui.ReadOnlyOptionDatabase.load_underlying', return_value=iv_history())
    def test_invalid_values_are_rejected_only_on_calculation(self, *mocks):
        for language in LANGUAGES:
            self.language(language)
            for key, invalid in [('premium', ''), ('premium', '-1'), ('premium', 'nan'),
                                 ('premium', 'abc'), ('strike', ''), ('strike', '0'),
                                 ('strike', '-1'), ('strike', 'inf'), ('spot', '0'),
                                 ('spot', '-1'), ('spot', 'nan'), ('spot', 'abc')]:
                with self.subTest(language=language, field=key, value=invalid):
                    self.fill()
                    entry = self.window.numeric_entries[key]
                    entry.delete(0, 'end')
                    entry.insert(0, invalid)
                    self.assertEqual(entry.get(), invalid)
                    self.window.analyze_button.invoke()
                    prefix = 'Unable to calculate' if language == 'en' else '无法计算'
                    self.assertIn(prefix, self.window.status.get())
                    self.assertEqual(self.window.annual_text.get(), '—')
                    self.assertEqual(self.window.percentile_text.get(), '—')
                    self.assertEqual(self.window.iv_percentile_text.get(), '—')
            # Preserve the existing optional-spot and zero-premium semantics.
            self.fill()
            self.window.spot.set('')
            self.window.calculate()
            self.assertIn('%', self.window.annual_text.get())
            self.fill()
            self.window.premium.set('0')
            self.window.calculate()
            self.assertIn('%', self.window.annual_text.get())

    @patch('option_quant.put_gui.now_utc', return_value=NOW)
    @patch('option_quant.put_gui.ReadOnlyOptionDatabase.load_underlying', return_value=iv_history())
    def test_database_dropdown_and_calendar_preserve_all_three_results(self, *mocks):
        for language in LANGUAGES:
            self.language(language)
            self.fill()
            self.window.reference_button.invoke()
            self.assertIn('2026-10-28', self.window.expiry_box['values'])
            self.window.expiry_box.current(0)
            self.window.expiry_box.event_generate('<<ComboboxSelected>>')
            self.assertEqual(self.window.expiry.get(), '2026-10-28')
            self.window.calculate()
            before = (self.window.percentile_text.get(), self.window.annual_text.get(),
                      self.window.iv_percentile_text.get())
            self.assertEqual(before[0], '33.3%')
            self.assertEqual(before[2], '50.0%')
            self.assertEqual(before[1], f'{(200 - 2.5275) / 9000 * 365 / 30:.2%}')
            choices = self.window.expiry_box['values']
            with patch.object(self.window, 'calculate') as calculate:
                self.window.calendar_button.invoke()
                picker = self.window.calendar_window
                self.assertEqual(picker.displayed_month, date(2026, 10, 1))
                picker.day_buttons[28].invoke()
                calculate.assert_not_called()
            self.assertEqual(self.window.expiry.get(), '2026-10-28')
            self.assertEqual(self.window.expiry_box['values'], choices)
            self.assertEqual(self.window.annual_text.get(), '—')
            self.window.calculate()
            self.assertEqual((self.window.percentile_text.get(), self.window.annual_text.get(),
                              self.window.iv_percentile_text.get()), before)
            self.window.open_calendar()
            self.window.calendar_window.day_buttons[29].invoke()
            self.assertEqual(self.window.expiry.get(), '2026-10-29')
            self.assertEqual(self.window.expiry_box['values'], choices)

    @patch('option_quant.put_gui.now_utc', return_value=NOW)
    def test_calendar_fallback_cancel_today_and_live_translation(self, *mocks):
        self.fill()
        self.window.expiry.set('unfinished')
        self.window.open_calendar()
        picker = self.window.calendar_window
        self.assertEqual(picker.displayed_month, date(2026, 9, 1))
        self.assertEqual(picker.title(), 'Choose Expiration Date')
        self.window.open_calendar()
        self.assertIs(self.window.calendar_window, picker)
        picker.next_button.invoke()
        self.language('zh_CN')
        self.assertEqual(picker.title(), '选择到期日')
        self.assertEqual(picker.month_label['text'], '2026年10月')
        self.assertEqual(picker.cancel_button['text'], '取消')
        picker.cancel_button.invoke()
        self.assertEqual(self.window.expiry.get(), 'unfinished')
        self.window.open_calendar()
        self.window.calendar_window.today_button.invoke()
        self.assertEqual(self.window.expiry.get(), '2026-09-28')
        self.window.calculate()
        self.assertIn('到期日须晚于纽约今天', self.window.status.get())

    def test_calendar_month_rollover_leap_day_and_date_bounds(self):
        self.window.expiry.set('2027-12-31')
        self.window.open_calendar()
        picker = self.window.calendar_window
        picker.next_button.invoke()
        self.assertEqual(picker.displayed_month, date(2028, 1, 1))
        picker.next_button.invoke()
        self.assertIn(29, picker.day_buttons)
        picker.day_buttons[29].invoke()
        self.assertEqual(self.window.expiry.get(), '2028-02-29')
        for text, direction, disabled in [('0001-01-01', -1, 'previous_button'),
                                           ('9999-12-31', 1, 'next_button')]:
            self.window.expiry.set(text)
            self.window.open_calendar()
            picker = self.window.calendar_window
            before = picker.displayed_month
            picker.move_month(direction)
            self.assertEqual(picker.displayed_month, before)
            self.assertTrue(getattr(picker, disabled).instate(['disabled']))
            picker.destroy()

    def test_calendar_keyboard_selection_and_escape_do_not_calculate(self):
        self.window.expiry.set('2026-10-28')
        with patch.object(self.window, 'calculate') as calculate:
            self.window.open_calendar()
            picker = self.window.calendar_window
            button = picker.day_buttons[29]
            self.focus(button)
            button.event_generate('<Return>')
            self.assertEqual(self.window.expiry.get(), '2026-10-29')
            self.window.open_calendar()
            picker = self.window.calendar_window
            self.focus(picker.day_buttons[29])
            picker.event_generate('<Escape>')
            self.assertFalse(picker.winfo_exists())
            self.assertEqual(self.window.expiry.get(), '2026-10-29')
            calculate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
