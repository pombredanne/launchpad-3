# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test harness for Launchpad/Mailman doctests."""

import doctest
import unittest


def test_suite():
    suite = unittest.TestSuite()

    # If Mailman isn't even configured to be built, then there's really
    # nothing we can do.  This isn't completely correct because it doesn't
    # catch the case where Mailman was built, but then the 'build' key was set
    # back to false.  This is really better than testing to see if the Mailman
    # package is importable because, that we really want to do in the doctest!
    from canonical.config import config
    if config.mailman.build.build:
        # These tests will only be run when Mailman is enabled.
        test = doctest.DocFileSuite(
            'test-lpmm.txt',
            optionflags = (doctest.ELLIPSIS     |
                           doctest.REPORT_NDIFF |
                           doctest.NORMALIZE_WHITESPACE),
            )
        suite.addTest(test)
    return suite
