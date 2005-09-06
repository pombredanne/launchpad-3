# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

from unittest import main
from doctest import DocTestSuite

def test_suite():
    import canonical.launchpad.validators
    return DocTestSuite(canonical.launchpad.validators)

if __name__ == '__main__':
    DEFAULT = test_suite()
    unittest.main('DEFAULT')

