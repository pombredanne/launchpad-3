# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for methods of BranchMergeQueue."""


from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.interfaces.branchmergequeue import IBranchMergeQueue
from lp.code.model.branchmergequeue import BranchMergeQueue
from lp.testing import TestCaseWithFactory


class TestIBranchMergeProposal(TestCaseWithFactory):
    """Test IBranchMergeQueue interface."""

    layer = DatabaseFunctionalLayer

    def test_implements_interface(self):
        queue = BranchMergeQueue()
        verifyObject(IBranchMergeQueue, queue)
