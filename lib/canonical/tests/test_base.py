# Copyright 2004 Canonical Ltd.  All rights reserved.

import unittest
from zope.testing.doctestunit import DocTestSuite
import canonical.base

def test_suite():
    suite = DocTestSuite(canonical.base)
    return suite

def _test():
    import doctest, test_dbschema
    return doctest.testmod(test_dbschema)

if __name__ == "__main__":
    _test()

