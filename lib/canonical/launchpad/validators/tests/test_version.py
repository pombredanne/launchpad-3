# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

import doctest, unittest

def test_suite():
    import canonical.launchpad.validators.version
    return doctest.DocTestSuite(canonical.launchpad.validators.version)

DEFAULT = test_suite()

if __name__ == '__main__':
    unittest.main(defaultTest='DEFAULT')

