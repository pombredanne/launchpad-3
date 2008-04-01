# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

from unittest import main, TestSuite
from doctest import DocTestSuite

def test_suite():
    suite = TestSuite()

    # Get the doctests in __init__.py.
    from canonical.launchpad import validators
    suite.addTest(DocTestSuite(validators))

    from canonical.launchpad.validators import name, url, version, email
    suite.addTest(DocTestSuite(url))
    suite.addTest(DocTestSuite(version))
    suite.addTest(DocTestSuite(name))
    suite.addTest(DocTestSuite(email))
    return suite

if __name__ == '__main__':
    DEFAULT = test_suite()
    unittest.main('DEFAULT')

