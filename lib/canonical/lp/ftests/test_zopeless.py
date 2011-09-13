# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Tests to make sure that initZopeless works as expected.
"""

from doctest import DocTestSuite
import unittest
import warnings

from canonical.database.sqlbase import alreadyInstalledMsg
from canonical.lp import initZopeless
from canonical.testing.layers import LaunchpadScriptLayer


class TestInitZopeless(unittest.TestCase):

    layer = LaunchpadScriptLayer

    def test_initZopelessTwice(self):
        # Hook the warnings module, so we can verify that we get the expected
        # warning.  The warnings module has two key functions, warn and
        # warn_explicit, the first calling the second. You might, therefore,
        # think that we should hook the second, to catch all warnings in one
        # place.  However, from Python 2.6, both of these are replaced with
        # entries into a C extension if available, and the C implementation of
        # the first will not call a monkeypatched Python implementation of the
        # second.  Therefore, we hook warn, as is the one actually called by
        # the particular code we are interested in testing.
        original_warn = warnings.warn
        warnings.warn = self.warn_hooked
        self.warned = False
        try:
            # Calling initZopeless with the same arguments twice should return
            # the exact same object twice, but also emit a warning.
            try:
                tm1 = initZopeless(dbuser='launchpad')
                tm2 = initZopeless(dbuser='launchpad')
                self.failUnless(tm1 is tm2)
                self.failUnless(self.warned)
            finally:
                tm1.uninstall()
        finally:
            # Put the warnings module back the way we found it.
            warnings.warn = original_warn

    def warn_hooked(self, message, category=None, stacklevel=1):
        self.failUnlessEqual(alreadyInstalledMsg, str(message))
        self.warned = True


def test_isZopeless():
    """
    >>> from canonical.lp import isZopeless

    >>> isZopeless()
    False

    >>> tm = initZopeless(dbuser='launchpad')
    >>> isZopeless()
    True

    >>> tm.uninstall()
    >>> isZopeless()
    False

    """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestInitZopeless))
    doctests = DocTestSuite()
    doctests.layer = LaunchpadScriptLayer
    suite.addTest(doctests)
    return suite
