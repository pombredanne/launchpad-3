# Copyright 2004 Canonical Ltd.  All rights reserved.

import unittest
from zope.testing.doctest import DocTestSuite, ELLIPSIS
import canonical.encoding

def test_suite():
    suite = DocTestSuite(canonical.encoding, optionflags=ELLIPSIS)
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
