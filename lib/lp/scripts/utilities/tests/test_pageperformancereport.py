# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the pageperformancereport script."""

__metaclass__ = type

import unittest

from lp.testing import TestCase

from lp.scripts.utilities.pageperformancereport import (
    Category,
    SQLiteRequestTimes,
    )

class FakeOptions:
    timeout = 12
    db_file = None
    pageids = True
    top_urls = True

    def __init__(self, **kwargs):
        """Assign all arguments as attributes."""
        self.__dict__.update(kwargs)

class FakeRequest:
    def __init__(self, url, app_seconds, sql_statements=None, 
                 sql_seconds=None, pageid=None):
        self.url = url
        self.pageid = pageid
        self.app_seconds = app_seconds
        self.sql_statements = sql_statements
        self.sql_seconds = sql_seconds


class TestSQLiteTimes(TestCase):
    """Tests the SQLiteTimes backend."""

    def setUp(self):
        TestCase.setUp(self)
        self.categories = [
            Category('All', '.*'), Category('Test', '.*test.*'),
            Category('Bugs', '.*bugs.*')]
        self.db = SQLiteRequestTimes(self.categories, FakeOptions())
        self.addCleanup(self.db.close)

    def test_histogram_table_is_created(self):
        # A histogram table with one row by histogram bin should be
        # present.
        self.db.cur.execute('SELECT bin FROM histogram')
        # Default timeout is 12.
        self.assertEquals(
            range(18), [row[0] for row in self.db.cur.fetchall()])

    def test_add_report_null_missing_sql_fields(self):
        # Ensure that missing sql_statements and sql_time values are
        # inserted as NULL.
        self.db.add_request(FakeRequest('/', 10.0))
        # Request should be inserted into the All category (index 0)
        # and the normal request table.
        self.db.cur.execute(
            '''SELECT sql_statements, sql_time 
               FROM category_request WHERE category = 0''')
        self.assertEquals([(None, None)], self.db.cur.fetchall())

        self.db.cur.execute(
            """SELECT sql_statements, sql_time
               FROM request WHERE url = '/'""")
        self.assertEquals([(None, None)], self.db.cur.fetchall())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
