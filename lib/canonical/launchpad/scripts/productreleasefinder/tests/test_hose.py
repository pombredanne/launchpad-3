"""Tests for canonical.launchpad.scripts.productreleasefinder.hose."""

import os
import shutil
import tempfile
import unittest

from canonical.testing import reset_logging
from hct.scaffold import Scaffold


class Hose_Logging(unittest.TestCase):
    def testCreatesDefaultLogger(self):
        """Hose creates a default logger."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        from logging import Logger
        h = Hose()
        self.failUnless(isinstance(h.log, Logger))

    def testCreatesChildLogger(self):
        """Hose creates a child logger if given a parent."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        from logging import getLogger
        parent = getLogger("foo")
        h = Hose(log_parent=parent)
        self.assertEquals(h.log.parent, parent)


class Hose_Filter(unittest.TestCase):
    def testCreatesFilterObject(self):
        """Hose creates a Filter object."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        from canonical.launchpad.scripts.productreleasefinder.filter import (
            Filter)
        h = Hose()
        self.failUnless(isinstance(h.filter, Filter))

    def testDefaultsFiltersToEmptyDict(self):
        """Hose creates Filter object with empty dictionary."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        h = Hose()
        self.assertEquals(h.filter.filters, [])

    def testCreatesFiltersWithGiven(self):
        """Hose creates Filter object with dictionary given."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        from canonical.launchpad.scripts.productreleasefinder.filter import (
            FilterPattern)
        pattern = FilterPattern("foo", "http:", "e*")
        h = Hose([pattern])
        self.assertEquals(len(h.filter.filters), 1)
        self.assertEquals(h.filter.filters[0], pattern)


class Hose_Urls(Scaffold):
    def testCallsReduceWork(self):
        """Hose constructor calls reduceWork function."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        h = self.wrapped(Hose)
        self.assertEquals(h.called["reduceWork"], True)

    def testPassesUrlList(self):
        """Hose constructor passes url list to reduceWork."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        from canonical.launchpad.scripts.productreleasefinder.filter import (
            FilterPattern)
        pattern = FilterPattern("foo", "http://archive.ubuntu.com/", "e*")
        h = self.wrapped(Hose, [pattern])
        self.assertEquals(h.called_args["reduceWork"][0][0],
                          ["http://archive.ubuntu.com/"])

    def testSetsUrlProperty(self):
        """Hose constructor sets urls property to reduceWork return value."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        class TestHose(Hose):
            def reduceWork(self, url_list):
                return "wibble"

        h = TestHose()
        self.assertEquals(h.urls, "wibble")


class Hose_ReduceWork(unittest.TestCase):
    def testEmptyList(self):
        """Hose.reduceWork returns empty list when given one."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        h = Hose()
        self.assertEquals(h.reduceWork([]), [])

    def testReducedList(self):
        """Hose.reduceWork returns same list when nothing to do."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        h = Hose()
        self.assertEquals(h.reduceWork(["http://localhost/", "file:///usr/"]),
                          ["http://localhost/", "file:///usr/"])

    def testReducesList(self):
        """Hose.reduceWork removes children elements from list."""
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        h = Hose()
        self.assertEquals(h.reduceWork(["http://localhost/",
                                        "http://localhost/foo/bar/",
                                        "http://localhost/wibble/",
                                        "file:///usr/"]),
                          ["http://localhost/", "file:///usr/"])


class Hose_LimitWalk(unittest.TestCase):

    def setUp(self):
        self.release_root = tempfile.mkdtemp()
        self.release_url = 'file://' + self.release_root

    def tearDown(self):
        shutil.rmtree(self.release_root, ignore_errors=True)
        reset_logging()

    def testHoseLimitsWalk(self):
        # Test that the hose limits the directory walk to places that
        # could contain a match.
        
        # Set up the releases tree:
        for directory in ['bar',
                          'foo',
                          'foo/1.0',
                          'foo/1.0/source',
                          'foo/1.0/x64',
                          'foo/1.5',
                          'foo/1.5/source',
                          'foo/2.0',
                          'foo/2.0/source']:
            os.mkdir(os.path.join(self.release_root, directory))
        for releasefile in ['foo/1.0/foo-1.0.tar.gz',
                            'foo/1.0/source/foo-1.0.tar.gz',
                            'foo/1.0/source/foo-2.0.tar.gz',
                            'foo/1.0/x64/foo-1.0.tar.gz',
                            'foo/1.5/source/foo-1.5.tar.gz',
                            'foo/2.0/source/foo-2.0.tar.gz']:
            fp = open(os.path.join(self.release_root, releasefile), 'wb')
            fp.write('data')
            fp.close()

        # Run the hose over the test data
        from canonical.launchpad.scripts.productreleasefinder.hose import Hose
        from canonical.launchpad.scripts.productreleasefinder.filter import (
            FilterPattern)
        pattern = FilterPattern("key", self.release_url,
                                "foo/1.*/source/foo-1.*.tar.gz")
        hose = Hose([pattern])

        prefix_len = len(self.release_url)
        matched = []
        unmatched = []
        for key, url in hose:
            if key is None:
                unmatched.append(url[prefix_len:])
            else:
                matched.append(url[prefix_len:])

        # Make sure that the correct releases got found.
        self.assertEqual(sorted(matched),
                         ['/foo/1.0/source/foo-1.0.tar.gz',
                          '/foo/1.5/source/foo-1.5.tar.gz'])

        # The only unmatched files that get checked exist in
        # directories that are parents of potential matches.
        self.assertEqual(sorted(unmatched),
                         ['/foo/1.0/foo-1.0.tar.gz',
                          '/foo/1.0/source/foo-2.0.tar.gz'])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
