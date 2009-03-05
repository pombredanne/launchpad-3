# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

from doctest import DocTestSuite
from unittest import TestSuite

from canonical.launchpad.testing.systemdocs import setUp, tearDown
from canonical.testing import LaunchpadFunctionalLayer


def test_suite():
    suite = TestSuite()

    # Include the doctests in __init__.py.
    from canonical.launchpad import validators
    suite.addTest(DocTestSuite(validators))

    from canonical.launchpad.validators import (
        email, name, sourceforgeproject, url, version)
    suite.addTest(suitefor(email))
    suite.addTest(suitefor(name))
    suite.addTest(suitefor(sourceforgeproject))
    suite.addTest(suitefor(url))
    suite.addTest(suitefor(version))

    return suite


def suitefor(module):
    """Make a doctest suite with common setUp and tearDown functions."""
    suite = DocTestSuite(module, setUp=setUp, tearDown=tearDown)
    # We have to invoke the LaunchpadFunctionalLayer in order to
    # initialize the ZCA machinery, which is a pre-requisite for using
    # login().
    suite.layer = LaunchpadFunctionalLayer
    return suite


if __name__ == '__main__':
    DEFAULT = test_suite()
    import unittest
    unittest.main('DEFAULT')
