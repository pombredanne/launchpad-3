# Copyright 2005 Canonical Ltd.  All rights reserved.
"""Librarian garbage collection tests"""

__metaclass__ = type

from cStringIO import StringIO
from unittest import TestCase, TestLoader

from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestCase
from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.scripts import supermirror_rewritemap
from canonical.lp import initZopeless
from canonical.config import config


class TestRewriteMapScript(LaunchpadFunctionalTestCase):
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        LaunchpadFunctionalTestCase.setUp(
            self, dbuser=config.supermirror.dbuser)
        self.login()

    def test_file_generation(self):
        """A simple smoke test for the supermirror_rewritemap cronscript."""
        file = StringIO()
        supermirror_rewritemap.write_map(file)
        lines = file.getvalue().splitlines()
        self.failUnless('~name12/gnome-terminal/main\t00/00/00/0f' in lines,
                'expected line not found in %r' % (lines,))

    def test_file_generation_junk_product(self):
        """Like test_file_generation, but demonstrating a +junk product."""
        file = StringIO()
        supermirror_rewritemap.write_map(file)
        lines = file.getvalue().splitlines()
        self.failUnless('~spiv/+junk/feature\t00/00/00/16' in lines,
                'expected line not found in %r' % (lines,))


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

