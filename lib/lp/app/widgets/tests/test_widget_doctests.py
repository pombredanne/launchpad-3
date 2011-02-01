# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest, doctest
from canonical.testing.layers import DatabaseFunctionalLayer

def test_suite():
    suite = unittest.TestSuite()
    suite.layer = DatabaseFunctionalLayer
    suite.addTest(doctest.DocTestSuite('lp.app.widgets.password'))
    suite.addTest(doctest.DocTestSuite('lp.app.widgets.textwidgets'))
    suite.addTest(doctest.DocTestSuite('lp.app.widgets.date'))
    return suite
