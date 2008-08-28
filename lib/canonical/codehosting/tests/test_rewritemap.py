# Copyright 2005-2008 Canonical Ltd.  All rights reserved.

"""Librarian garbage collection tests"""

__metaclass__ = type

from StringIO import StringIO
from unittest import TestLoader

import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.codehosting import branch_id_to_path
from canonical.config import config
from canonical.launchpad.interfaces import BranchType, IBranchSet
from canonical.launchpad.testing import LaunchpadObjectFactory, TestCase
from canonical.codehosting import rewritemap
from canonical.testing import LaunchpadZopelessLayer


class TestRewriteMapScript(TestCase):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.factory = LaunchpadObjectFactory()

    def getRewriteFileLines(self):
        """Create the rewrite file and return the contents."""
        LaunchpadZopelessLayer.switchDbUser(config.supermirror.dbuser)
        file = StringIO()
        rewritemap.write_map(file)
        return file.getvalue().splitlines()

    def testFileGeneration(self):
        # A simple smoke test for the rewritemap cronscript.
        lines = self.getRewriteFileLines()
        self.failUnless('~name12/gnome-terminal/main\t00/00/00/0f' in lines,
                'expected line not found in %r' % (lines,))

    def testFileGenerationJunkProduct(self):
        # Like test_file_generation, but demonstrating a +junk product.
        lines = self.getRewriteFileLines()
        self.failUnless('~spiv/+junk/feature\t00/00/00/16' in lines,
                'expected line not found in %r' % (lines,))

    def testPrivateBranchNotWritten(self):
        # Private branches do not have entries in the rewrite file.
        # Make the branch private by setting the visibility team.
        branch_unique_name = '~name12/gnome-terminal/scanned'
        branch = getUtility(IBranchSet).getByUniqueName(branch_unique_name)
        branch.private = True
        transaction.commit()
        # Now create the rewrite map.
        lines = self.getRewriteFileLines()
        self.failIf('~name12/gnome-terminal/scanned\t00/00/00/1b' in lines,
                    'private branch %s should not be in %r' %
                    (branch_unique_name, lines))

    def testPrivateStackedBranch(self):
        # Branches stacked on private branches don't have entries in the
        # rewrite file.
        stacked_on_branch = self.factory.makeBranch(private=True)
        stacked_branch = self.factory.makeBranch()
        branch_name = stacked_branch.unique_name
        branch_id = stacked_branch.id
        removeSecurityProxy(stacked_branch).stacked_on = stacked_on_branch
        transaction.commit()
        # Now create the rewrite map.
        expected_line = '%s\t%s' % (branch_name, branch_id_to_path(branch_id))
        lines = self.getRewriteFileLines()
        self.failIf(
            expected_line in lines,
            'private branch %s should not be in %r' % (branch_name, lines))

    def testRemoteBranchNotWritten(self):
        # Remote branches do not have entries in the rewrite file.
        branch_unique_name = '~name12/gnome-terminal/scanned'
        branch = getUtility(IBranchSet).getByUniqueName(branch_unique_name)
        branch.branch_type = BranchType.REMOTE
        transaction.commit()
        # Now create the rewrite map.
        lines = self.getRewriteFileLines()
        self.failIf('~name12/gnome-terminal/scanned\t00/00/00/1b' in lines,
                    'remote branch %s should not be in %r' %
                    (branch_unique_name, lines))

def test_suite():
    return TestLoader().loadTestsFromName(__name__)

