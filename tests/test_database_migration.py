# Copyright © 2026 Bo Hu. All rights reserved.
#
# Created: October 7, 2026

from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

import pandas as pd

from option_quant.database import OptionDatabase


class OptionTypeMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'options.db'
        self.database = OptionDatabase(str(self.path))
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute('''CREATE TABLE option_snapshots (
                snapshot_time TEXT, underlying TEXT, underlying_price REAL,
                option_code TEXT, expiry TEXT, strike REAL, dte INTEGER,
                last REAL, bid REAL, ask REAL, volume REAL, open_interest INTEGER,
                iv REAL, delta REAL, gamma REAL, vega REAL, theta REAL)''')
            connection.executemany(
                'INSERT INTO option_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                [self.row('US.TESTP1'), self.row('US.TESTP2')])

    @staticmethod
    def row(code):
        return ('2026-10-07T20:00:00.000000Z', 'US.TEST', 101.25, code,
                '2026-11-20', 90.0, 44, None, 1.2, 1.4, 0.0, 123, 55.5,
                -0.2, 0.01, 0.15, -0.02)

    def query(self, sql):
        with closing(sqlite3.connect(self.path)) as connection:
            return connection.execute(sql).fetchall()

    def frame(self, timestamp, code='US.TESTP1', underlying='US.TEST', option_type=None):
        columns = [row[1] for row in self.query('PRAGMA table_info(option_snapshots)')]
        data = dict(zip([name for name in columns if name != 'option_type'], self.row(code)))
        data['snapshot_time'] = timestamp
        data['underlying'] = underlying
        if option_type is not None:
            data['option_type'] = option_type
        return pd.DataFrame([data])

    def test_old_table_backfilled_without_changing_history(self):
        before = self.query('SELECT rowid, * FROM option_snapshots ORDER BY rowid')
        schema_before = self.query('PRAGMA table_info(option_snapshots)')
        self.assertTrue(self.database.migrate_option_type())
        after = self.query('SELECT rowid, * FROM option_snapshots ORDER BY rowid')
        self.assertEqual([row[:-1] for row in after], before)
        self.assertEqual([row[-1] for row in after], ['PUT', 'PUT'])
        schema = self.query('PRAGMA table_info(option_snapshots)')
        self.assertEqual(schema[:-1], schema_before)
        self.assertEqual(schema[-1][1:3], ('option_type', 'TEXT'))

    def test_running_twice_is_noop(self):
        self.assertTrue(self.database.migrate_option_type())
        before = self.query('SELECT rowid, * FROM option_snapshots ORDER BY rowid')
        self.assertFalse(self.database.migrate_option_type())
        self.assertEqual(self.query('SELECT rowid, * FROM option_snapshots ORDER BY rowid'), before)
        self.assertEqual(len(self.query('PRAGMA table_info(option_snapshots)')), 18)

    def test_existing_column_preserves_call_and_null_values(self):
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute('ALTER TABLE option_snapshots ADD COLUMN option_type TEXT')
            connection.execute("UPDATE option_snapshots SET option_type='CALL' WHERE rowid=1")
        before = self.query('SELECT rowid, * FROM option_snapshots ORDER BY rowid')
        schema = self.query('PRAGMA table_info(option_snapshots)')
        self.assertFalse(self.database.migrate_option_type())
        self.assertEqual(self.query('SELECT rowid, * FROM option_snapshots ORDER BY rowid'), before)
        self.assertEqual(self.query('PRAGMA table_info(option_snapshots)'), schema)

    def test_save_migrates_even_when_all_input_rows_are_duplicates(self):
        frame = self.frame('2026-10-08T01:00:00Z')  # Still October 7 in New York.
        self.assertEqual(self.database.save_snapshots(frame), (0, 1))
        self.assertEqual(self.query('SELECT option_type FROM option_snapshots'), [('PUT',), ('PUT',)])
        self.assertEqual(self.database.save_snapshots(frame), (0, 1))

    def test_duplicate_key_ignores_option_type_but_respects_ny_day(self):
        self.database.migrate_option_type()
        self.assertEqual(self.database.save_snapshots(
            self.frame('2026-10-08T03:59:59Z', option_type='CALL')), (0, 1))
        self.assertEqual(self.database.save_snapshots(
            self.frame('2026-10-08T04:00:00Z', option_type='PUT')), (1, 0))
        self.assertEqual(self.database.save_snapshots(
            self.frame('2026-10-07T21:00:00Z', code='US.TESTC1', option_type='CALL')), (1, 0))
        self.assertEqual(self.database.save_snapshots(
            self.frame('2026-10-07T21:00:00Z', underlying='US.OTHER', option_type='PUT')), (1, 0))
        self.assertEqual(self.query('SELECT COUNT(*) FROM option_snapshots'), [(5,)])

    def test_legacy_incoming_frame_still_appends_without_collection_changes(self):
        self.assertEqual(self.database.save_snapshots(
            self.frame('2026-10-07T21:00:00Z', code='US.TESTP3')), (1, 0))
        self.assertEqual(self.query('SELECT option_type FROM option_snapshots ORDER BY rowid'),
                         [('PUT',), ('PUT',), (None,)])

    def test_failed_backfill_rolls_back_column_and_data(self):
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute('''CREATE TRIGGER reject_update BEFORE UPDATE ON option_snapshots
                                  BEGIN SELECT RAISE(ABORT, 'test backfill failure'); END''')
        before = self.query('SELECT rowid, * FROM option_snapshots ORDER BY rowid')
        with self.assertRaises(sqlite3.IntegrityError):
            self.database.migrate_option_type()
        self.assertEqual(len(self.query('PRAGMA table_info(option_snapshots)')), 17)
        self.assertEqual(self.query('SELECT rowid, * FROM option_snapshots ORDER BY rowid'), before)
