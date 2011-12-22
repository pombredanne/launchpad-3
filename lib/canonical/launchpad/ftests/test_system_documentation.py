# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Test the examples included in the system documentation in
lib/canonical/launchpad/doc.
"""
# pylint: disable-msg=C0103

import logging
import os
import unittest

from zope.testing.cleanup import cleanUp

from canonical.testing.layers import (
    AppServerLayer,
    FunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing import browser
from lp.testing.systemdocs import (
    LayeredDocFileSuite,
    setGlobs,
    setUp,
    tearDown,
    )


here = os.path.dirname(os.path.realpath(__file__))


def layerlessTearDown(test):
    """Clean up any Zope registrations."""
    cleanUp()


# Files that have special needs can construct their own suite
special = {
    # No setup or teardown at all, since it is demonstrating these features.
    'old-testing.txt': LayeredDocFileSuite(
        '../doc/old-testing.txt', layer=FunctionalLayer),
    'webservice-configuration.txt': LayeredDocFileSuite(
        '../doc/webservice-configuration.txt',
        setUp=setGlobs, tearDown=layerlessTearDown, layer=None),
    # This test is actually run twice to prove that the AppServerLayer
    # properly isolates the database between tests.
    'launchpadlib.txt': LayeredDocFileSuite(
        '../doc/launchpadlib.txt',
        layer=AppServerLayer,
        setUp=browser.setUp, tearDown=browser.tearDown,),
    'launchpadlib2.txt': LayeredDocFileSuite(
        '../doc/launchpadlib.txt',
        layer=AppServerLayer,
        setUp=browser.setUp, tearDown=browser.tearDown,),
    }


def test_suite():
    suite = unittest.TestSuite()

    # Add special needs tests
    for key in sorted(special):
        special_suite = special[key]
        suite.addTest(special_suite)

    testsdir = os.path.abspath(
        os.path.normpath(os.path.join(here, '..', 'doc')))

    # Add tests using default setup/teardown
    filenames = [filename
                 for filename in os.listdir(testsdir)
                 if filename.lower().endswith('.txt')
                    and filename not in special]
    # Sort the list to give a predictable order.  We do this because when
    # tests interfere with each other, the varying orderings that os.listdir
    # gives on different people's systems make reproducing and debugging
    # problems difficult.  Ideally the test harness would stop the tests from
    # being able to interfere with each other in the first place.
    #   -- Andrew Bennetts, 2005-03-01.
    filenames.sort()
    for filename in filenames:
        path = os.path.join('../doc/', filename)
        one_test = LayeredDocFileSuite(
            path, setUp=setUp, tearDown=tearDown,
            layer=LaunchpadFunctionalLayer,
            stdout_logging_level=logging.WARNING)
        suite.addTest(one_test)

    return suite


if __name__ == '__main__':
    unittest.main(test_suite())
