# -*- coding: utf-8 -*-
"""Tests for canonical.launchpad.productreleasefinder.log."""

__copyright__ = "Copyright © 2005 Canonical Ltd."
__author__    = "Scott James Remnant <scott@canonical.com>"


import unittest


class GetLogger(unittest.TestCase):
    def testLogger(self):
        """get_logger returns a Logger instance."""
        from canonical.launchpad.scripts.productreleasefinder.log import get_logger
        from logging import Logger
        self.failUnless(isinstance(get_logger("test"), Logger))

    def testNoParent(self):
        """get_logger works if no parent is given."""
        from canonical.launchpad.scripts.productreleasefinder.log import get_logger
        self.assertEquals(get_logger("test").name, "test")

    def testRootParent(self):
        """get_logger works if root logger is given."""
        from canonical.launchpad.scripts.productreleasefinder.log import get_logger
        from logging import root
        self.assertEquals(get_logger("test", root).name, "test")

    def testNormalParent(self):
        """get_logger works if non-root logger is given."""
        from canonical.launchpad.scripts.productreleasefinder.log import get_logger
        from logging import getLogger
        parent = getLogger("foo")
        self.assertEquals(get_logger("test", parent).name, "foo.test")

    def testDeepParent(self):
        """get_logger works if deep-level logger is given."""
        from canonical.launchpad.scripts.productreleasefinder.log import get_logger
        from logging import getLogger
        parent1 = getLogger("foo")
        parent2 = getLogger("foo.bar")
        self.assertEquals(get_logger("test", parent2).name, "foo.bar.test")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
