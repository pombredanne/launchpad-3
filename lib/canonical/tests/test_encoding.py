# Copyright 2004 Canonical Ltd.  All rights reserved.

import unittest
from zope.testing.doctestunit import DocTestSuite
import canonical.encoding

def test_suite():
    suite = DocTestSuite(canonical.encoding)
    return suite
DEFAULT = test_suite()


if __name__ == '__main__':
    unittest.main(defaultTest='DEFAULT')
