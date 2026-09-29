# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: September 13, 2026

"""A small, non-modal Tk calendar that returns canonical ISO dates."""

import calendar
from datetime import date
import tkinter as tk
from tkinter import ttk

from option_quant.gui_i18n import message


class DatePicker(tk.Toplevel):
    def __init__(self, master, *, selected: date, today: date, translator, on_select):
        super().__init__(master)
        self.withdraw()
        self.transient(master)
        self.resizable(False, False)
        self.translator = translator
        self.on_select = on_select
        self.selected = selected
        self.today = today
        self.displayed_month = selected.replace(day=1)
        self._labels = []
        self.day_buttons = {}

        content = ttk.Frame(self, padding=12)
        content.pack(fill="both", expand=True)
        navigation = ttk.Frame(content)
        navigation.grid(row=0, column=0, columnspan=7, sticky="ew", pady=(0, 10))
        self.previous_button = self.localized(ttk.Button(navigation, command=lambda: self.move_month(-1)), 'calendar_previous')
        self.previous_button.pack(side="left")
        self.month_label = ttk.Label(navigation, anchor="center", width=22)
        self.month_label.pack(side="left", fill="x", expand=True, padx=8)
        self.next_button = self.localized(ttk.Button(navigation, command=lambda: self.move_month(1)), 'calendar_next')
        self.next_button.pack(side="right")
        for column, key in enumerate(['calendar_monday', 'calendar_tuesday', 'calendar_wednesday',
                                      'calendar_thursday', 'calendar_friday', 'calendar_saturday', 'calendar_sunday']):
            self.localized(ttk.Label(content, anchor="center"), key).grid(row=1, column=column, sticky="ew")
            content.columnconfigure(column, weight=1)
        self.days_frame = ttk.Frame(content)
        self.days_frame.grid(row=2, column=0, columnspan=7, sticky="ew", pady=6)
        footer = ttk.Frame(content)
        footer.grid(row=3, column=0, columnspan=7, sticky="ew")
        self.today_button = self.localized(ttk.Button(footer, command=lambda: self.select(self.today)), 'calendar_today')
        self.today_button.pack(side="left")
        self.cancel_button = self.localized(ttk.Button(footer, command=self.destroy), 'calendar_cancel')
        self.cancel_button.pack(side="right")
        self.bind('<Escape>', lambda event: self.destroy())
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.refresh_language()
        self.update_idletasks()
        x = max(0, min(master.winfo_rootx() + 40, self.winfo_screenwidth() - self.winfo_reqwidth()))
        y = max(0, min(master.winfo_rooty() + 100, self.winfo_screenheight() - self.winfo_reqheight()))
        self.geometry(f'+{x}+{y}')
        self.deiconify()
        self.day_buttons[selected.day].focus_set()

    def localized(self, widget, key):
        self._labels.append((widget, key))
        return widget

    def refresh_language(self):
        self.title(self.translator.render(message('calendar_title')))
        for widget, key in self._labels:
            widget.configure(text=self.translator.render(message(key)))
        self.render_month()

    def move_month(self, offset):
        month_index = (self.displayed_month.year - 1) * 12 + self.displayed_month.month - 1 + offset
        if 0 <= month_index < 9999 * 12:
            year, month = divmod(month_index, 12)
            self.displayed_month = date(year + 1, month + 1, 1)
            self.render_month()

    def render_month(self):
        month = self.displayed_month
        self.month_label.configure(text=self.translator.render(message(
            'calendar_month_year', month=message(f'calendar_month_{month.month}'), year=month.year)))
        self.previous_button.state(['disabled'] if month == date.min else ['!disabled'])
        self.next_button.state(['disabled'] if month == date(9999, 12, 1) else ['!disabled'])
        for widget in self.days_frame.winfo_children():
            widget.destroy()
        self.day_buttons.clear()
        weeks = calendar.Calendar(firstweekday=calendar.MONDAY).monthdayscalendar(month.year, month.month)
        for row in range(6):
            for column in range(7):
                day = weeks[row][column] if row < len(weeks) else 0
                self.days_frame.columnconfigure(column, weight=1, uniform='day')
                if day:
                    value = month.replace(day=day)
                    button = ttk.Button(self.days_frame, text=str(day), width=4,
                                        command=lambda selected=value: self.select(selected))
                    button.bind('<Return>', lambda event, selected=value: self.select(selected))
                    if value == self.selected:
                        button.state(['pressed'])
                    self.day_buttons[day] = button
                    widget = button
                else:
                    widget = ttk.Label(self.days_frame, width=4)
                widget.grid(row=row, column=column, sticky="nsew", padx=1, pady=1)

    def select(self, selected):
        self.on_select(selected.isoformat())
        self.destroy()
        return 'break'
