# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

from unittest import main, TestSuite
from doctest import DocTestSuite
from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.testing import LaunchpadFunctionalLayer

def test_suite():
    suite = TestSuite()

    # Include the doctests in __init__.py.
    from canonical.launchpad import validators
    suite.addTest(DocTestSuite(validators))

    from canonical.launchpad.validators import name, url, version, email
    suite.addTest(suitefor(url))
    suite.addTest(suitefor(version))
    suite.addTest(suitefor(name))
    suite.addTest(suitefor(email))
    return suite

def suitefor(module):
    """Make a doctest suite with common setUp and tearDown functions."""
    suite = DocTestSuite(module,
                         setUp=common_setUp,
                         tearDown=common_tearDown)
    # We have to invoke the LaunchpadFunctionalLayer in order to
    # initialize the ZCA machinery, which is a pre-requisite for using
    # login().
    suite.layer = LaunchpadFunctionalLayer
    return suite

def common_setUp(test):
    """Setup common to all validator unit tests."""
    login(ANONYMOUS)

def common_tearDown(test):
    """Teardown common to all validator unit tests."""
    logout()

if __name__ == '__main__':
    DEFAULT = test_suite()
    unittest.main('DEFAULT')

