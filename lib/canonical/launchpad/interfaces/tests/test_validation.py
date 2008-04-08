# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

from unittest import TestSuite
from doctest import DocTestSuite, ELLIPSIS, NORMALIZE_WHITESPACE
from canonical.launchpad.testing.systemdocs import setUp, tearDown
from canonical.testing import LaunchpadFunctionalLayer

def test_suite():
    suite = TestSuite()
    import canonical.launchpad.interfaces.validation
    test = DocTestSuite(
        canonical.launchpad.interfaces.validation,
        setUp=setUp,
        tearDown=tearDown,
        optionflags=ELLIPSIS | NORMALIZE_WHITESPACE
        )
    # We have to invoke the LaunchpadFunctionalLayer in order to
    # initialize the ZCA machinery, which is a pre-requisite for using
    # login().
    test.layer = LaunchpadFunctionalLayer
    suite.addTest(test)
    return suite

if __name__ == '__main__':
    DEFAULT = test_suite()
    import unittest
    unittest.main('DEFAULT')

