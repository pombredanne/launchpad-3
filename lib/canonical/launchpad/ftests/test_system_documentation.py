"""Test the examples included in the system documentation in
lib/canonical/launchpad/doc."""

import unittest
import os
from canonical.functional import FunctionalTestSetup
from canonical.functional import FunctionalDocFileSuite

here = os.path.dirname(os.path.realpath(__file__))

def test_suite():
    suite = unittest.TestSuite()
    testsdir = os.path.abspath(
            os.path.normpath(os.path.join(here, '..', 'doc'))
            )

    filenames = [filename
                 for filename in os.listdir(testsdir)
                 if filename.lower().endswith('.txt')
                 ]
    for filename in filenames:
        path = os.path.join('../doc/', filename)
        suite.addTest(FunctionalDocFileSuite(path))
    return suite

if __name__ == '__main__':
    unittest.main(test_suite())
