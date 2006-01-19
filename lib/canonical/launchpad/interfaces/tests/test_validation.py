# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

from unittest import main, TestSuite
from doctest import DocTestSuite, ELLIPSIS, NORMALIZE_WHITESPACE

def test_suite():
    suite = TestSuite()
    import canonical.launchpad.interfaces.validation
    suite.addTest(DocTestSuite(
        canonical.launchpad.interfaces.validation,
        optionflags=ELLIPSIS | NORMALIZE_WHITESPACE
        ))
    return suite

if __name__ == '__main__':
    DEFAULT = test_suite()
    unittest.main('DEFAULT')

