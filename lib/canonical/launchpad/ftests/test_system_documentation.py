"""Test the examples included in the system documentation in
lib/canonical/launchpad/doc."""

import unittest
import os
from canonical.functional import FunctionalDocFileSuite
import sqlos.connection
from canonical.launchpad.ftests.harness import \
        LaunchpadTestSetup, _disconnect_sqlos, _reconnect_sqlos
from zope.testing.doctest import DocFileSuite

here = os.path.dirname(os.path.realpath(__file__))

def setUp(test):
    sqlos.connection.connCache = {}
    LaunchpadTestSetup().setUp()
    _reconnect_sqlos()

def tearDown(test):
    _disconnect_sqlos()
    sqlos.connection.connCache = {}
    LaunchpadTestSetup().tearDown()

# Files that have special needs can construct their own suite
special = {

    # No setup or teardown at all, since it is demonstrating these features
    'testing.txt': DocFileSuite('../doc/testing.txt')

    }

def test_suite():
    suite = unittest.TestSuite()

    # Add special needs tests
    for special_suite in special.values():
        suite.addTest(special_suite)

    testsdir = os.path.abspath(
            os.path.normpath(os.path.join(here, '..', 'doc'))
            )

    # Add tests using default setup/teardown
    filenames = [filename
                 for filename in os.listdir(testsdir)
                 if filename.lower().endswith('.txt')
                    and filename not in special
                 ]
    # XXX: Sort the list to give a predictable order.  We do this because when
    # tests interfere with each other, the varying orderings that os.listdir
    # gives on different people's systems make reproducing and debugging
    # problems difficult.  Ideally the test harness would stop the tests from
    # being able to interfere with each other in the first place.
    #   -- Andrew Bennetts, 2005-03-01.
    filenames.sort()
    for filename in filenames:
        path = os.path.join('../doc/', filename)
        suite.addTest(FunctionalDocFileSuite(
            path, setUp=setUp, tearDown=tearDown
            ))

    return suite

if __name__ == '__main__':
    unittest.main(test_suite())
