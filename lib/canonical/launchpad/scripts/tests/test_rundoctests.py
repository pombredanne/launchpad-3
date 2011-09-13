# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from doctest import DocTestSuite
import unittest

from canonical.testing import reset_logging


def tearDown(test):
    reset_logging()


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite('canonical.launchpad.scripts.sort_sql'))
    suite.addTest(DocTestSuite(
        'canonical.launchpad.scripts.logger', tearDown=tearDown
        ))
    suite.addTest(DocTestSuite('canonical.launchpad.scripts'))
    return suite
