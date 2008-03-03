# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test harness for Answer Tracker related unit tests.

"""

__metaclass__ = type

__all__ = []

import unittest

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from canonical.testing import LaunchpadFunctionalLayer

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(LayeredDocFileSuite('questioncontextmenu.txt'))
    suite.addTest(LayeredDocFileSuite('question-subscribe_me.txt',
                  setUp=setUp, tearDown=tearDown,
                  layer=LaunchpadFunctionalLayer))
    return suite

if __name__ == '__main__':
    unittest.main()

