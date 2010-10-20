# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for methods of BranchMergeQueue."""

from __future__ import with_statement

import simplejson

from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.code.errors import InvalidMergeQueueConfig
from lp.code.interfaces.branchmergequeue import IBranchMergeQueue
from lp.code.model.branchmergequeue import BranchMergeQueue
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class TestBranchMergeQueueInterface(TestCaseWithFactory):
    """Test IBranchMergeQueue interface."""

    layer = DatabaseFunctionalLayer

    def test_implements_interface(self):
        queue = self.factory.makeBranchMergeQueue()
        IStore(BranchMergeQueue).add(queue)
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


class TestBranchMergeQueue(TestCaseWithFactory):
    """Test the functions of the BranchMergeQueue."""

    layer = DatabaseFunctionalLayer

    def test_branches(self):
        """Test that a merge queue can get all its managed branches."""
        store = IStore(BranchMergeQueue)

        queue = self.factory.makeBranchMergeQueue()
        store.add(queue)

        branch = self.factory.makeBranch()
        store.add(branch)
        with person_logged_in(branch.owner):
            branch.addToQueue(queue)

        self.assertEqual(
            list(queue.branches),
            [branch])

    def test_setMergeQueueConfig(self):
        """Test that the configuration is set properly."""
        queue = self.factory.makeBranchMergeQueue()
        config = unicode(simplejson.dumps({
            'test': 'make test'}))

        queue.setMergeQueueConfig(config)

        self.assertEqual(queue.configuration, config)

    def test_setMergeQueueConfig_invalid_json(self):
        """Test that invalid json can't be set as the config."""
        queue = self.factory.makeBranchMergeQueue()
        self.assertRaises(
            InvalidMergeQueueConfig,
            queue.setMergeQueueConfig,
            'abc')
