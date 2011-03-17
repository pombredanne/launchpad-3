# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from doctest import DocTestSuite
import unittest

import lp.soyuz.scripts.gina.handlers


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite(lp.soyuz.scripts.gina.handlers))
    return suite
