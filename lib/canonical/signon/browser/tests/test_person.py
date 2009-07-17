# Copyright 2008,2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(LayeredDocFileSuite(
        'person-rename-account-with-openid.txt',
        setUp=setUp, tearDown=tearDown,
        layer=DatabaseFunctionalLayer))
    return suite


if __name__ == '__main__':
    unittest.main()
