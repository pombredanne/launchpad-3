# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest, doctest
from canonical.testing.layers import LaunchpadFunctionalLayer

def test_suite():
    suite = unittest.TestSuite()
    suite.layer = LaunchpadFunctionalLayer
    suite.addTest(doctest.DocTestSuite('canonical.widgets.password'))
    suite.addTest(doctest.DocTestSuite('canonical.widgets.textwidgets'))
    suite.addTest(doctest.DocTestSuite('canonical.widgets.date'))
    return suite
