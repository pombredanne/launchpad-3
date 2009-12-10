# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

from zope.testing.doctest import DocTestSuite

import lp.soyuz.scripts.gina.handlers


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite(lp.soyuz.scripts.gina.handlers))
    return suite

