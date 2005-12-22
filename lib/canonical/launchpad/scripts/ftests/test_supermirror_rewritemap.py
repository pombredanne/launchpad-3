# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Librarian garbage collection tests"""

__metaclass__ = type

from unittest import TestCase, TestSuite, makeSuite
from cStringIO import StringIO

from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestSetup
from canonical.launchpad.scripts import supermirror_rewritemap
from canonical.lp import initZopeless
from canonical.config import config


class TestRewriteMapScript(TestCase):
    def setUp(self):
        LaunchpadFunctionalTestSetup(dbuser=config.supermirror.dbuser).setUp()
        from canonical.launchpad.ftests import login, ANONYMOUS
        login(ANONYMOUS)

    def tearDown(self):
        LaunchpadFunctionalTestSetup().tearDown()

    def test_file_generation(self):
        """A simple smoke test for the supermirror_rewritemap cronscript."""
        file = StringIO()
        supermirror_rewritemap.main(file)
        lines = file.getvalue().splitlines()
        self.failUnless('~name12/gnome-terminal/main\t00/00/00/0f' in lines,
                'expected line not found in %r' % (lines,))


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(TestRewriteMapScript))
    return suite

