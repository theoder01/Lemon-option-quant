# Copyright © 2026 Bo Hu. All rights reserved.
"""Presentation regressions: sizing, semantics, focus and retained content."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from option_quant.put_gui import PutAnalysisWindow, create_root
from option_quant.gui_strings import LANGUAGES
from option_quant.gui_theme import COLORS
from test_put_preview import NOW
from test_put_iv_preview import iv_history


class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.root=create_root()
        self.root.minsize(1,1)
        self.addCleanup(self.root.destroy)
        self.root.tk.call('tk','scaling',96/72)
        self.root.geometry('1280x940+0+0')
        self.window=PutAnalysisWindow(self.root,Path('presentation-fixture.db'))
        self.root.update()

    def fill(self):
        w=self.window
        w.premium.set('2');w.strike.set('90');w.spot.set('100');w.expiry.set('2026-10-28')
        p=w.existing_page
        p.strike.set('100');p.spot.set('110');p.close_premium.set('0.30');p.expiry.set('2026-10-18')

    @patch('option_quant.put_gui.now_utc',return_value=NOW)
    @patch('option_quant.put_gui.ReadOnlyOptionDatabase.load_underlying',return_value=iv_history())
    def test_empty_success_error_and_unavailable_states(self,*mocks):
        for page,tab in [(self.window,self.window.new_page),(self.window.existing_page,self.window.existing_page)]:
            self.window.notebook.select(tab);self.root.update()
            self.assertTrue(page.empty_label.winfo_ismapped())
            self.assertEqual(page.annual_text.get(),'—')
            self.fill();page.calculate();self.root.update()
            self.assertFalse(page.empty_label.winfo_ismapped())
            self.assertTrue(page.details.winfo_ismapped())
            self.assertIn('Capital, fees & returns',page.details.get('1.0','end'))
            self.assertIn(page.status_label['style'],('Muted.TLabel','Warning.TLabel'))
            page.strike.set('0');page.calculate();self.root.update()
            self.assertEqual(page.status_label['style'],'Error.TLabel')
            self.assertIn('Unable to calculate',page.status.get())
            self.assertTrue(page.empty_label.winfo_ismapped())
            self.assertEqual(page.annual_text.get(),'—')
        self.fill()
        with patch('option_quant.put_gui.ReadOnlyOptionDatabase.load_underlying',return_value=iv_history().iloc[-1:]):
            self.window.calculate()
        self.assertEqual(self.window.iv_percentile_text.get(),'—')
        self.assertIn('Insufficient',self.window.iv_status_text.get())
        self.window.set_message(self.window.percentile_text,'0.0%')
        self.assertEqual(self.window.percentile_text.get(),'0.0%')

    def test_database_summary_full_path_and_button_keyboard(self):
        w=self.window
        self.assertEqual(w.database_name.get(),'presentation-fixture.db')
        self.assertFalse(w.database_entry.winfo_ismapped())
        w.path_button.invoke();self.root.update()
        self.assertTrue(w.database_entry.winfo_ismapped())
        self.assertEqual(w.database_entry.get(),w.database_path.get())
        w.toggle_database_path();self.root.update()
        self.assertFalse(w.database_entry.winfo_ismapped())
        w.database_path.set('another-fixture.db')
        self.assertEqual(w.database_name.get(),'another-fixture.db')
        # Native focus traversal still reaches the date entry after the ticker.
        w.ticker_box.focus_force();self.root.update()
        w.ticker_box.event_generate('<Tab>');self.root.update()
        self.assertIs(self.root.focus_get(),w.expiry_box)

    @patch('option_quant.put_gui.now_utc',return_value=NOW)
    @patch('option_quant.put_gui.ReadOnlyOptionDatabase.load_underlying',return_value=iv_history())
    def test_details_keep_every_rendered_message_and_switch_languages(self,*mocks):
        self.fill()
        for page in (self.window,self.window.existing_page):
            page.calculate()
        for code in LANGUAGES:
            self.window.language.set(LANGUAGES[code]);self.window.change_language()
            for page in (self.window,self.window.existing_page):
                actual=page.details.get('1.0','end').replace('\t','')
                for item in page._detail_messages.messages:
                    for line in page.translator.render(item).replace(' | ','\n').splitlines():
                        self.assertIn(line,actual)
        style=ttk.Style(self.root)
        self.assertEqual(style.lookup('Metric.TLabel','foreground'),COLORS['text'])
        self.assertNotEqual(style.lookup('TEntry','bordercolor',('focus',)),style.lookup('TEntry','bordercolor'))

    def test_layout_bounds_at_supported_sizes_scales_and_languages(self):
        for scale in (1,1.5,2):
            self.window.destroy()
            self.root.tk.call('tk','scaling',scale*96/72)
            self.window=PutAnalysisWindow(self.root,Path('presentation-fixture.db'))
            for width,height in ((1280,940),(760,620),(1600,960)):
                self.root.geometry(f'{round(width*scale)}x{round(height*scale)}+0+0')
                for code in LANGUAGES:
                    self.window.language.set(LANGUAGES[code]);self.window.change_language()
                    for page,tab in [(self.window,self.window.new_page),(self.window.existing_page,self.window.existing_page)]:
                        with self.subTest(scale=scale,width=width,language=code,page=type(page).__name__):
                            self.window.notebook.select(tab);self.root.update()
                            viewport=page.viewport; canvas=viewport.canvas
                            self.assertTrue(viewport.scrollbar.winfo_ismapped())
                            self.assertLessEqual(viewport.scrollbar.winfo_rootx()+viewport.scrollbar.winfo_width(),
                                                 viewport.winfo_rootx()+viewport.winfo_width())
                            self.assertEqual(page._stacked,width<980)
                            self.assertLessEqual(viewport.body.winfo_width(),round(1440*viewport.scale)+2)
                            widgets=[page.ticker_box,page.expiry_box,page.calendar_button,page.analyze_button,*page.numeric_entries.values(),*page.result_cards]
                            for widget in widgets:
                                left=widget.winfo_rootx()-canvas.winfo_rootx()
                                self.assertGreaterEqual(left,0)
                                self.assertLessEqual(left+widget.winfo_width(),canvas.winfo_width()+1)
                            page.analyze_button.focus_force();self.root.update()
                            top=page.analyze_button.winfo_rooty()-canvas.winfo_rooty()
                            self.assertGreaterEqual(top,0)
                            self.assertLessEqual(top+page.analyze_button.winfo_height(),canvas.winfo_height()+1)
                            self.assertLessEqual(self.window.language_box.winfo_rootx()+self.window.language_box.winfo_width(),self.root.winfo_rootx()+self.root.winfo_width())


if __name__=='__main__': unittest.main()
