# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test harness for Answer Tracker related unit tests.

"""

__metaclass__ = type

__all__ = []

import unittest

from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(LayeredDocFileSuite('question-subscribe_me.txt',
                  setUp=setUp, tearDown=tearDown,
                  layer=DatabaseFunctionalLayer))
    suite.addTest(LayeredDocFileSuite('views.txt',
                  setUp=setUp, tearDown=tearDown,
                  layer=DatabaseFunctionalLayer))
    suite.addTest(LayeredDocFileSuite('faq-views.txt',
                  setUp=setUp, tearDown=tearDown,
                  layer=LaunchpadFunctionalLayer))
    return suite

if __name__ == '__main__':
    unittest.main()
