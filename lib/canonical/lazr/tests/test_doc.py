# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test harness for LAZR doctests."""

__metaclass__ = type
__all__ = []

import doctest
import os

from zope.testing.cleanup import cleanUp

DOCTEST_FLAGS = (
    doctest.ELLIPSIS |
    doctest.NORMALIZE_WHITESPACE |
    doctest.REPORT_NDIFF)

def setUp(test):
    """All classes should be new-style."""
    test.globs['__metaclass__'] = type
    test.globs['__file__'] = test.filename

def tearDown(test):
    """Run registered clean-up function."""
    cleanUp()


def test_suite():
    """See `zope.testing.testrunner`."""
    tests = sorted(
        ['../doc/%s' % name
         for name in os.listdir(
            os.path.join(os.path.dirname(__file__), '../doc'))
         if name.endswith('.txt')])
    return doctest.DocFileSuite(
        setUp=setUp, tearDown=tearDown, optionflags=DOCTEST_FLAGS, *tests)
