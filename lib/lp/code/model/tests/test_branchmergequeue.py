# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for methods of BranchMergeQueue."""

import simplejson

from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.interfaces.branchmergequeue import IBranchMergeQueue
from lp.code.model.branchmergequeue import BranchMergeQueue
from lp.testing import TestCaseWithFactory


class TestBranchMergeQueueInterface(TestCaseWithFactory):
    """Test IBranchMergeQueue interface."""

    layer = DatabaseFunctionalLayer

    def test_implements_interface(self):
        queue = BranchMergeQueue()
        verifyObject(IBranchMergeQueue, queue)


class TestBranchMergeQueueSource(TestCaseWithFactory):
    """Test the methods of IBranchMergeQueueSource."""

    layer = DatabaseFunctionalLayer

    def test_new(self):
        owner = self.factory.makePerson()
        name = u'SooperQueue'
        description = u'This is Sooper Queue'
        config = unicode(simplejson.dumps({'test': 'make check'}))

        queue = BranchMergeQueue.new(
            name, owner, owner, description, config)

        self.assertEqual(queue.name, name)
        self.assertEqual(queue.owner, owner)
        self.assertEqual(queue.registrant, owner)
        self.assertEqual(queue.description, description)
        self.assertEqual(queue.configuration, config)
