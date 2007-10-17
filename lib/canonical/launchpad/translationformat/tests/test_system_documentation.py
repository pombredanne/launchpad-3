# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""
Test the examples included in the system documentation in
lib/canonical/launchpad/translationformat/doc.
"""

import unittest
import logging
import os
from zope.testing.doctest import REPORT_NDIFF, NORMALIZE_WHITESPACE, ELLIPSIS
from zope.testing.doctest import DocFileSuite

from canonical.functional import FunctionalDocFileSuite
from canonical.launchpad.ftests.test_system_documentation import (
    setUp, tearDown)
from canonical.testing import LaunchpadFunctionalLayer

here = os.path.dirname(os.path.realpath(__file__))

default_optionflags = REPORT_NDIFF | NORMALIZE_WHITESPACE | ELLIPSIS

# Files that have special needs can construct their own suite
special = {
    'gettext_po_parser.txt': DocFileSuite(
        '../doc/gettext_po_parser.txt', optionflags=default_optionflags)
    }


def test_suite():
    suite = unittest.TestSuite()

    # Add special needs tests
    for key in sorted(special):
        special_suite = special[key]
        suite.addTest(special_suite)

    testsdir = os.path.abspath(
            os.path.normpath(os.path.join(here, '..', 'doc'))
            )

    # Add tests using default setup/teardown
    # Sort the list to give a predictable order.  We do this because when
    # tests interfere with each other, the varying orderings that os.listdir
    # gives on different people's systems make reproducing and debugging
    # problems difficult.  Ideally the test harness would stop the tests from
    # being able to interfere with each other in the first place.
    #   -- Andrew Bennetts, 2005-03-01.
    filenames = sorted(
        filename
        for filename in os.listdir(testsdir)
            if (os.path.splitext(filename)[1] == '.txt' and
                filename not in special)
        )

    for filename in filenames:
        path = os.path.join('../doc/', filename)
        one_test = FunctionalDocFileSuite(
            path, setUp=setUp, tearDown=tearDown,
            layer=LaunchpadFunctionalLayer, optionflags=default_optionflags,
            stdout_logging_level=logging.WARNING
            )
        suite.addTest(one_test)

    return suite


if __name__ == '__main__':
    unittest.main(test_suite())
