# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the pageperformancereport script."""

__metaclass__ = type

import unittest

from lp.testing import TestCase

from lp.scripts.utilities.pageperformancereport import (
    Category,
    SQLiteRequestTimes,
    Stats,
    )

class FakeOptions:
    timeout = 4
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


class FakeStats(Stats):
    def __init__(self, **kwargs):
        # Override the constructor to just store the values.
        self.__dict__.update(kwargs)

FAKE_REQUESTS = [
    FakeRequest('/', 0.5, pageid='+root'),
    FakeRequest('/bugs', 4.5, 56, 3.0, pageid='+bugs'),
    FakeRequest('/bugs', 4.2, 56, 2.2, pageid='+bugs'),
    FakeRequest('/bugs', 5.5, 76, 4.0, pageid='+bugs'),
    FakeRequest('/ubuntu', 2.5, 6, 2.0, pageid='+distribution'),
    FakeRequest('/launchpad', 3.5, 3, 3.0, pageid='+project'),
    FakeRequest('/bzr', 2.5, 4, 2.0, pageid='+project'),
    FakeRequest('/bugs/1', 20.5, 567, 14.0, pageid='+bug'),
    FakeRequest('/bugs/1', 15.5, 567, 9.0, pageid='+bug'),
    FakeRequest('/bugs/5', 1.5, 30, 1.2, pageid='+bug'),
    FakeRequest('/lazr', 1.0, 16, 0.3, pageid='+project'),
    FakeRequest('/drizzle', 0.9, 11, 1.3, pageid='+project'),
    ]


# The category stats computed for the above 12 requests.
CATEGORY_STATS = [
    (Category('All', ''), FakeStats(
        total_hits=12, total_time=62.60, mean=5.22, median=2.5, std=5.99,
        total_sqltime=42, mean_sqltime=3.82, median_sqltime=2.2,
        std_sqltime=3.89,
        total_sqlstatements=1392, mean_sqlstatements=126.55,
        median_sqlstatments=43, std_sqlstatements=208.94,
        histogram=[[0, 2], [1, 2], [2, 2], [3, 1], [4, 2], [5, 3]],
        )),
    (Category('Test', ''), FakeStats()),
    (Category('Bugs', ''), FakeStats(
        total_hits=6, total_time=51.70, mean=8.62, median=5.0, std=6.90,
        total_sqltime=33.40, mean_sqltime=5.57, median_sqltime=3.0,
        std_sqltime=4.52,
        total_sqlstatements=1352, mean_sqlstatements=225.33,
        median_sqlstatements=66, std_sqlstatements=241.96,
        histogram=[[0, 0], [1, 1], [2, 0], [3, 0], [4, 2], [5, 3]],
        )),
    ]


# The top 3 URL stats computed for the above 12 requests.
TOP_3_URL_STATS = [
    ('/bugs/1', FakeStats(
        total_hits=2, total_time=36.0, mean=18.0, median=15.5, std=2.50,
        total_sqltime=23.0, mean_sqltime=11.5, median_sqltime=9.0,
        std_sqltime=2.50,
        total_sqlstatements=1134, mean_sqlstatements=567.0,
        median_sqlstatments=567, std_statements=0)),
    ('/bugs', FakeStats()),
    ('/launchpad', FakeStats()),
    ]


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
        # Default timeout is 4.
        self.assertEquals(
            range(6), [row[0] for row in self.db.cur.fetchall()])

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

    def setUpRequests(self):
        """Insert some requests into the db."""
        for r in FAKE_REQUESTS:
            self.db.add_request(r)

    def assertStatsAreEquals(self, expected, results):
        self.assertEquals(
            len(expected), len(results),
            'Wrong number of results: %d != %d' % (
                len(expected), len(results)))
        for idx in range(len(results)):
            self.assertEquals(expected[idx][0], results[idx][0],
                "Wrong key for results %d: %s != %s" % (
                    idx, expected[idx][0], results[idx][0]))
            key = results[idx][0]
            self.assertEquals(expected[idx][1].text(), results[idx][1].text(),
                "Wrong stats for results %d (%s): %s != %s" % (
                    idx, key, expected[idx][1].text(), results[idx][1].text()
                    ))
            self.assertEquals(
                expected[idx][1].histogram, results[idx][1].histogram,
                "Wrong histogram for results %d (%s): %s != %s" % (
                    idx, key, expected[idx][1].histogram,
                    results[idx][1].histogram))

    def test_get_category_times(self):
        self.setUpRequests()
        category_times = self.db.get_category_times()
        self.assertStatsAreEquals(CATEGORY_STATS, category_times)

    def test_get_url_times(self):
        self.setUpRequests()
        url_times = self.db.get_top_urls_times(3)
        self.assertStatsAreEquals(TOP_3_URL_STATS, url_times)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
