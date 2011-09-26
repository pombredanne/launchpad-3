__metaclass__ = type

import logging

from bzrlib.branch import Branch

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.code.bzr import (
    get_branch_formats,
    RepositoryFormat,
    )
from lp.codehosting.upgrade import Upgrader
from lp.testing import (
    temp_dir,
    TestCaseWithFactory,
    )


class TestUpgrader(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def upgrade(self, target_dir, branch):
        return Upgrader(target_dir, logging.getLogger()).upgrade(branch)

    def test_simple_upgrade(self):
        self.useBzrBranches(direct_database=True)
        branch, tree = self.create_branch_and_tree(format='knit')
        target_dir = self.useContext(temp_dir())
        upgraded = Branch.open(self.upgrade(target_dir, branch))
        self.assertEqual(
            get_branch_formats(upgraded)[2], RepositoryFormat.BZR_CHK_2A)
