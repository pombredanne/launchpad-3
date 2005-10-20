# Copyright 2004 Canonical Ltd.  All rights reserved.

import unittest
from zope.testing.doctestunit import DocTestSuite
import canonical.uuid

def test_suite():
    suite = DocTestSuite(canonical.uuid)
    return suite

if __name__ == "__main__":
    DEFAULT = test_suite()
    unittest.main(defaultTest='DEFAULT')

