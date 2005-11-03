# Copyright 2004 Canonical Ltd.  All rights reserved.

import unittest
from zope.testing.doctest import DocTestSuite, ELLIPSIS
import canonical.cachedproperty

def test_suite():
    suite = DocTestSuite(canonical.cachedproperty, optionflags=ELLIPSIS)
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
