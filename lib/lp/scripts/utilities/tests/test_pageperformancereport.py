# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the pageperformancereport script."""

__metaclass__ = type

from lp.scripts.utilities.pageperformancereport import (
    Category,
    Histogram,
    OnlineApproximateMedian,
    OnlineStats,
    OnlineStatsCalculator,
    RequestTimes,
    Stats,
    )
from lp.testing import TestCase


class FakeOptions:
    timeout = 5
    db_file = None
    pageids = True
    top_urls = 3
    resolution = 1

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
    # Median is an approximation.
    # Real values are: 2.50, 2.20, 30
    (Category('All', ''), FakeStats(
        total_hits=12, total_time=62.60, mean=5.22, median=4.20, std=5.99,
        total_sqltime=42, mean_sqltime=3.82, median_sqltime=3.0,
        std_sqltime=3.89,
        total_sqlstatements=1392, mean_sqlstatements=126.55,
        median_sqlstatements=56, std_sqlstatements=208.94,
        histogram=[[0, 2], [1, 2], [2, 2], [3, 1], [4, 2], [5, 3]],
        )),
    (Category('Test', ''), FakeStats(
        histogram=[[0, 0], [1, 0], [2, 0], [3, 0], [4, 0], [5, 0]])),
    (Category('Bugs', ''), FakeStats(
        total_hits=6, total_time=51.70, mean=8.62, median=4.5, std=6.90,
        total_sqltime=33.40, mean_sqltime=5.57, median_sqltime=3,
        std_sqltime=4.52,
        total_sqlstatements=1352, mean_sqlstatements=225.33,
        median_sqlstatements=56, std_sqlstatements=241.96,
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
        median_sqlstatements=567, std_statements=0,
        histogram=[[0, 0], [1, 0], [2, 0], [3, 0], [4, 0], [5, 2]],
        )),
    ('/bugs', FakeStats(
        total_hits=3, total_time=14.2, mean=4.73, median=4.5, std=0.56,
        total_sqltime=9.2, mean_sqltime=3.07, median_sqltime=3,
        std_sqltime=0.74,
        total_sqlstatements=188, mean_sqlstatements=62.67,
        median_sqlstatements=56, std_sqlstatements=9.43,
        histogram=[[0, 0], [1, 0], [2, 0], [3, 0], [4, 2], [5, 1]],
        )),
    ('/launchpad', FakeStats(
        total_hits=1, total_time=3.5, mean=3.5, median=3.5, std=0,
        total_sqltime=3.0, mean_sqltime=3, median_sqltime=3, std_sqltime=0,
        total_sqlstatements=3, mean_sqlstatements=3,
        median_sqlstatements=3, std_sqlstatements=0,
        histogram=[[0, 0], [1, 0], [2, 0], [3, 1], [4, 0], [5, 0]],
        )),
    ]


# The pageid stats computed for the above 12 requests.
PAGEID_STATS = [
    ('+bug', FakeStats(
        total_hits=3, total_time=37.5, mean=12.5, median=15.5, std=8.04,
        total_sqltime=24.2, mean_sqltime=8.07, median_sqltime=9,
        std_sqltime=5.27,
        total_sqlstatements=1164, mean_sqlstatements=388,
        median_sqlstatements=567, std_sqlstatements=253.14,
        histogram=[[0, 0], [1, 1], [2, 0], [3, 0], [4, 0], [5, 2]],
        )),
    ('+bugs', FakeStats(
        total_hits=3, total_time=14.2, mean=4.73, median=4.5, std=0.56,
        total_sqltime=9.2, mean_sqltime=3.07, median_sqltime=3,
        std_sqltime=0.74,
        total_sqlstatements=188, mean_sqlstatements=62.67,
        median_sqlstatements=56, std_sqlstatements=9.43,
        histogram=[[0, 0], [1, 0], [2, 0], [3, 0], [4, 2], [5, 1]],
        )),
    ('+distribution', FakeStats(
        total_hits=1, total_time=2.5, mean=2.5, median=2.5, std=0,
        total_sqltime=2.0, mean_sqltime=2, median_sqltime=2, std_sqltime=0,
        total_sqlstatements=6, mean_sqlstatements=6,
        median_sqlstatements=6, std_sqlstatements=0,
        histogram=[[0, 0], [1, 0], [2, 1], [3, 0], [4, 0], [5, 0]],
        )),
    ('+project', FakeStats(
        total_hits=4, total_time=7.9, mean=1.98, median=1, std=1.08,
        total_sqltime=6.6, mean_sqltime=1.65, median_sqltime=1.3,
        std_sqltime=0.99,
        total_sqlstatements=34, mean_sqlstatements=8.5,
        median_sqlstatements=4, std_sqlstatements=5.32,
        histogram=[[0, 1], [1, 1], [2, 1], [3, 1], [4, 0], [5, 0]],
        )),
    ('+root', FakeStats(
        total_hits=1, total_time=0.5, mean=0.5, median=0.5, std=0,
        histogram=[[0, 1], [1, 0], [2, 0], [3, 0], [4, 0], [5, 0]],
        )),
    ]


class TestRequestTimes(TestCase):
    """Tests the RequestTimes backend."""

    def setUp(self):
        TestCase.setUp(self)
        self.categories = [
            Category('All', '.*'), Category('Test', '.*test.*'),
            Category('Bugs', '.*bugs.*')]
        self.db = RequestTimes(self.categories, FakeOptions())

    def setUpRequests(self):
        """Insert some requests into the db."""
        for r in FAKE_REQUESTS:
            self.db.add_request(r)

    def assertStatsAreEquals(self, expected, results):
        self.assertEquals(
            len(expected), len(results), 'Wrong number of results')
        for idx in range(len(results)):
            self.assertEquals(expected[idx][0], results[idx][0],
                "Wrong key for results %d" % idx)
            key = results[idx][0]
            self.assertEquals(expected[idx][1].text(), results[idx][1].text(),
                "Wrong stats for results %d (%s)" % (idx, key))
            self.assertEquals(
                Histogram.from_bins_data(expected[idx][1].histogram),
                results[idx][1].histogram,
                "Wrong histogram for results %d (%s)" % (idx, key))

    def test_get_category_times(self):
        self.setUpRequests()
        category_times = self.db.get_category_times()
        self.assertStatsAreEquals(CATEGORY_STATS, category_times)

    def test_get_url_times(self):
        self.setUpRequests()
        url_times = self.db.get_top_urls_times()
        self.assertStatsAreEquals(TOP_3_URL_STATS, url_times)

    def test_get_pageid_times(self):
        self.setUpRequests()
        pageid_times = self.db.get_pageid_times()
        self.assertStatsAreEquals(PAGEID_STATS, pageid_times)

    def test___add__(self):
        # Ensure that adding two RequestTimes together result in
        # a merge of their constituencies.
        db1 = self.db
        db2 = RequestTimes(self.categories, FakeOptions())
        db1.add_request(FakeRequest('/', 1.5, 5, 1.0, '+root'))
        db1.add_request(FakeRequest('/bugs', 3.5, 15, 1.0, '+bugs'))
        db2.add_request(FakeRequest('/bugs/1', 5.0, 30, 4.0, '+bug'))
        results = db1 + db2
        self.assertEquals(3, results.category_times[0][1].total_hits)
        self.assertEquals(0, results.category_times[1][1].total_hits)
        self.assertEquals(2, results.category_times[2][1].total_hits)
        self.assertEquals(1, results.pageid_times['+root'].total_hits)
        self.assertEquals(1, results.pageid_times['+bugs'].total_hits)
        self.assertEquals(1, results.pageid_times['+bug'].total_hits)
        self.assertEquals(1, results.url_times['/'].total_hits)
        self.assertEquals(1, results.url_times['/bugs'].total_hits)
        self.assertEquals(1, results.url_times['/bugs/1'].total_hits)

    def test_histogram_init_with_resolution(self):
        # Test that the resolution parameter increase the number of bins
        db = RequestTimes(
            self.categories, FakeOptions(timeout=4, resolution=1))
        self.assertEquals(5, db.histogram_width)
        self.assertEquals(1, db.histogram_resolution)
        db = RequestTimes(
            self.categories, FakeOptions(timeout=4, resolution=0.5))
        self.assertEquals(9, db.histogram_width)
        self.assertEquals(0.5, db.histogram_resolution)
        db = RequestTimes(
            self.categories, FakeOptions(timeout=4, resolution=2))
        self.assertEquals(3, db.histogram_width)
        self.assertEquals(2, db.histogram_resolution)


class TestOnlineStats(TestCase):
    """Tests for the OnlineStats class."""

    def test___add__(self):
        # Ensure that adding two OnlineStats merge all their constituencies.
        stats1 = OnlineStats(4, 1)
        stats1.update(FakeRequest('/', 2.0, 5, 1.5))
        stats2 = OnlineStats(4, 1)
        stats2.update(FakeRequest('/', 1.5, 2, 3.0))
        stats2.update(FakeRequest('/', 5.0, 2, 2.0))
        results = stats1 + stats2
        self.assertEquals(3, results.total_hits)
        self.assertEquals(2, results.median)
        self.assertEquals(9, results.total_sqlstatements)
        self.assertEquals(2, results.median_sqlstatements)
        self.assertEquals(6.5, results.total_sqltime)
        self.assertEquals(2.0, results.median_sqltime)
        self.assertEquals(
            Histogram.from_bins_data([[0, 0], [1, 1], [2, 1], [3, 1]]),
            results.histogram)


class TestOnlineStatsCalculator(TestCase):
    """Tests for the online stats calculator."""

    def setUp(self):
        TestCase.setUp(self)
        self.stats = OnlineStatsCalculator()

    def test_stats_for_empty_set(self):
        # Test the stats when there is no input.
        self.assertEquals(0, self.stats.count)
        self.assertEquals(0, self.stats.sum)
        self.assertEquals(0, self.stats.mean)
        self.assertEquals(0, self.stats.variance)
        self.assertEquals(0, self.stats.std)

    def test_stats_for_one_value(self):
        # Test the stats when adding one element.
        self.stats.update(5)
        self.assertEquals(1, self.stats.count)
        self.assertEquals(5, self.stats.sum)
        self.assertEquals(5, self.stats.mean)
        self.assertEquals(0, self.stats.variance)
        self.assertEquals(0, self.stats.std)

    def test_None_are_ignored(self):
        self.stats.update(None)
        self.assertEquals(0, self.stats.count)

    def test_stats_for_3_values(self):
        for x in [3, 6, 9]:
            self.stats.update(x)
        self.assertEquals(3, self.stats.count)
        self.assertEquals(18, self.stats.sum)
        self.assertEquals(6, self.stats.mean)
        self.assertEquals(6, self.stats.variance)
        self.assertEquals("2.45", "%.2f" % self.stats.std)

    def test___add___two_empty_together(self):
        stats2 = OnlineStatsCalculator()
        results = self.stats + stats2
        self.assertEquals(0, results.count)
        self.assertEquals(0, results.sum)
        self.assertEquals(0, results.mean)
        self.assertEquals(0, results.variance)

    def test___add___one_empty(self):
        stats2 = OnlineStatsCalculator()
        for x in [1, 2, 3]:
            self.stats.update(x)
        results = self.stats + stats2
        self.assertEquals(3, results.count)
        self.assertEquals(6, results.sum)
        self.assertEquals(2, results.mean)
        self.assertEquals(2, results.M2)

    def test___add__(self):
        stats2 = OnlineStatsCalculator()
        for x in [3, 6, 9]:
            self.stats.update(x)
        for x in [1, 2, 3]:
            stats2.update(x)
        results = self.stats + stats2
        self.assertEquals(6, results.count)
        self.assertEquals(24, results.sum)
        self.assertEquals(4, results.mean)
        self.assertEquals(44, results.M2)


SHUFFLE_RANGE_100 = [
    25, 79, 99, 76, 60, 63, 87, 77, 51, 82, 42, 96, 93, 58, 32, 66, 75,
     2, 26, 22, 11, 73, 61, 83, 65, 68, 44, 81, 64, 3, 33, 34, 15, 1,
    92, 27, 90, 74, 46, 57, 59, 31, 13, 19, 89, 29, 56, 94, 50, 49, 62,
    37, 21, 35, 5, 84, 88, 16, 8, 23, 40, 6, 48, 10, 97, 0, 53, 17, 30,
    18, 43, 86, 12, 71, 38, 78, 36, 7, 45, 47, 80, 54, 39, 91, 98, 24,
    55, 14, 52, 20, 69, 85, 95, 28, 4, 9, 67, 70, 41, 72,
    ]


class TestOnlineApproximateMedian(TestCase):
    """Tests for the approximate median computation."""

    def setUp(self):
        TestCase.setUp(self)
        self.estimator = OnlineApproximateMedian()

    def test_median_is_0_when_no_input(self):
        self.assertEquals(0, self.estimator.median)

    def test_median_is_true_median_for_n_lower_than_bucket_size(self):
        for x in range(9):
            self.estimator.update(x)
        self.assertEquals(4, self.estimator.median)

    def test_None_input_is_ignored(self):
        self.estimator.update(1)
        self.estimator.update(None)
        self.assertEquals(1, self.estimator.median)

    def test_approximate_median_is_good_enough(self):
        for x in SHUFFLE_RANGE_100:
            self.estimator.update(x)
        # True median is 50, 49 is good enough :-)
        self.assertIn(self.estimator.median, range(49,52))

    def test___add__(self):
        median1 = OnlineApproximateMedian(3)
        median1.buckets = [[1, 3], [4, 5], [6, 3]]
        median2 = OnlineApproximateMedian(3)
        median2.buckets = [[], [3, 6], [3, 7]]
        results = median1 + median2
        self.assertEquals([[1, 3], [6], [3, 7], [4]], results.buckets)


class TestHistogram(TestCase):
    """Test the histogram computation."""

    def test__init__(self):
        hist = Histogram(4, 1)
        self.assertEquals(4, hist.bins_count)
        self.assertEquals(1, hist.bins_size)
        self.assertEquals([[0, 0], [1, 0], [2, 0], [3, 0]], hist.bins)

    def test__init__bins_size_float(self):
        hist = Histogram(9, 0.5)
        self.assertEquals(9, hist.bins_count)
        self.assertEquals(0.5, hist.bins_size)
        self.assertEquals(
            [[0, 0], [0.5, 0], [1.0, 0], [1.5, 0],
             [2.0, 0], [2.5, 0], [3.0, 0], [3.5, 0], [4.0, 0]], hist.bins)

    def test_update(self):
        hist = Histogram(4, 1)
        hist.update(1)
        self.assertEquals(1, hist.count)
        self.assertEquals([[0, 0], [1, 1], [2, 0], [3, 0]], hist.bins)

        hist.update(1.3)
        self.assertEquals(2, hist.count)
        self.assertEquals([[0, 0], [1, 2], [2, 0], [3, 0]], hist.bins)

    def test_update_float_bin_size(self):
        hist = Histogram(4, 0.5)
        hist.update(1.3)
        self.assertEquals([[0, 0], [0.5, 0], [1.0, 1], [1.5, 0]], hist.bins)
        hist.update(0.5)
        self.assertEquals([[0, 0], [0.5, 1], [1.0, 1], [1.5, 0]], hist.bins)
        hist.update(0.6)
        self.assertEquals([[0, 0], [0.5, 2], [1.0, 1], [1.5, 0]], hist.bins)

    def test_update_max_goes_in_last_bin(self):
        hist = Histogram(4, 1)
        hist.update(9)
        self.assertEquals([[0, 0], [1, 0], [2, 0], [3, 1]], hist.bins)

    def test_bins_relative(self):
        hist = Histogram(4, 1)
        for x in range(4):
            hist.update(x)
        self.assertEquals(
            [[0, 0.25], [1, 0.25], [2, 0.25], [3, 0.25]], hist.bins_relative)

    def test_from_bins_data(self):
        hist = Histogram.from_bins_data([[0, 1], [1, 3], [2, 1], [3, 1]])
        self.assertEquals(4, hist.bins_count)
        self.assertEquals(1, hist.bins_size)
        self.assertEquals(6, hist.count)
        self.assertEquals([[0, 1], [1, 3], [2, 1], [3, 1]], hist.bins)

    def test___repr__(self):
        hist = Histogram.from_bins_data([[0, 1], [1, 3], [2, 1], [3, 1]])
        self.assertEquals(
            "<Histogram [[0, 1], [1, 3], [2, 1], [3, 1]]>", repr(hist))

    def test___eq__(self):
        hist1 = Histogram(4, 1)
        hist2 = Histogram(4, 1)
        self.assertEquals(hist1, hist2)

    def test__eq___with_data(self):
        hist1 = Histogram.from_bins_data([[0, 1], [1, 3], [2, 1], [3, 1]])
        hist2 = Histogram.from_bins_data([[0, 1], [1, 3], [2, 1], [3, 1]])
        self.assertEquals(hist1, hist2)

    def test___add__(self):
        hist1 = Histogram.from_bins_data([[0, 1], [1, 3], [2, 1], [3, 1]])
        hist2 = Histogram.from_bins_data([[0, 1], [1, 3], [2, 1], [3, 1]])
        hist3 = Histogram.from_bins_data([[0, 2], [1, 6], [2, 2], [3, 2]])
        total = hist1 + hist2
        self.assertEquals(hist3, total)
        self.assertEquals(12, total.count)

    def test___add___uses_widest(self):
        # Make sure that the resulting histogram is as wide as the widest one.
        hist1 = Histogram.from_bins_data([[0, 1], [1, 3], [2, 1], [3, 1]])
        hist2 = Histogram.from_bins_data(
            [[0, 1], [1, 3], [2, 1], [3, 1], [4, 2], [5, 3]])
        hist3 = Histogram.from_bins_data(
            [[0, 2], [1, 6], [2, 2], [3, 2], [4, 2], [5, 3]])
        self.assertEquals(hist3, hist1 + hist2)

    def test___add___interpolate_lower_resolution(self):
        # Make sure that when the other histogram has a bigger bin_size
        # the frequency is correctly split across the different bins.
        hist1 = Histogram.from_bins_data(
            [[0, 1], [0.5, 3], [1.0, 1], [1.5, 1]])
        hist2 = Histogram.from_bins_data(
            [[0, 1], [1, 2], [2, 3], [3, 1], [4, 1]])

        hist3 = Histogram.from_bins_data(
            [[0, 1.5], [0.5, 3.5], [1.0, 2], [1.5, 2],
            [2.0, 1.5], [2.5, 1.5], [3.0, 0.5], [3.5, 0.5], 
            [4.0, 0.5], [4.5, 0.5]])
        self.assertEquals(hist3, hist1 + hist2)

    def test___add___higher_resolution(self):
        # Make sure that when the other histogram has a smaller bin_size
        # the frequency is correctly added.
        hist1 = Histogram.from_bins_data([[0, 1], [1, 2], [2, 3]])
        hist2 = Histogram.from_bins_data(
            [[0, 1], [0.5, 3], [1.0, 1], [1.5, 1], [2.0, 3], [2.5, 1],
             [3, 4], [3.5, 2]])

        hist3 = Histogram.from_bins_data([[0, 5], [1, 4], [2, 7], [3, 6]])
        self.assertEquals(hist3, hist1 + hist2)
