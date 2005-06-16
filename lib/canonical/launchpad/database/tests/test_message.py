# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest
from zope.testing.doctestunit import DocTestSuite


def test_suite():
    return DocTestSuite('canonical.launchpad.database.message')

if __name__ == '__main__':
    unittest.main(test_suite())

