# Copyright 2005 Canonical Ltd.  All rights reserved.
"""Librarian garbage collection tests"""

__metaclass__ = type

from cStringIO import StringIO
from unittest import TestCase, TestLoader

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces import BranchType, IBranchSet
from canonical.launchpad.scripts import supermirror_rewritemap
from canonical.testing import LaunchpadZopelessLayer


class TestRewriteMapScript(TestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        TestCase.setUp(self)
        LaunchpadZopelessLayer.switchDbUser(config.supermirror.dbuser)

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

    def test_private_branch_not_written(self):
        """Private branches do not have entries in the rewrite file."""
        # Make the branch private by setting the visibility team.
        branch_unique_name = '~name12/gnome-terminal/scanned'
        branch = getUtility(IBranchSet).getByUniqueName(branch_unique_name)
        branch.private = True
        # Now create the rewrite map.
        file = StringIO()
        supermirror_rewritemap.write_map(file)
        lines = file.getvalue().splitlines()
        self.failIf('~name12/gnome-terminal/scanned\t00/00/00/1b' in lines,
                    'private branch %s should not be in %r' %
                    (branch_unique_name, lines))

    def test_remote_branch_not_written(self):
        """Remote branches do not have entries in the rewrite file."""
        branch_unique_name = '~name12/gnome-terminal/scanned'
        branch = getUtility(IBranchSet).getByUniqueName(branch_unique_name)
        branch.branch_type = BranchType.REMOTE
        # Now create the rewrite map.
        file = StringIO()
        supermirror_rewritemap.write_map(file)
        lines = file.getvalue().splitlines()
        self.failIf('~name12/gnome-terminal/scanned\t00/00/00/1b' in lines,
                    'remote branch %s should not be in %r' %
                    (branch_unique_name, lines))

def test_suite():
    return TestLoader().loadTestsFromName(__name__)

