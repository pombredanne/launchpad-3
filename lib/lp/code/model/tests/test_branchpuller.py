# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for the branch puller model code."""

__metaclass__ = type

from datetime import datetime, timedelta
import unittest

import pytz

import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.database.constants import UTC_NOW
from lp.code.interfaces.branch import BranchType, BranchTypeError
from lp.code.interfaces.branchpuller import IBranchPuller
from canonical.launchpad.testing import TestCase, TestCaseWithFactory
from canonical.testing.layers import DatabaseFunctionalLayer


class TestMirroringForHostedBranches(TestCaseWithFactory):
    """Tests for mirroring methods of a branch."""

    layer = DatabaseFunctionalLayer
    branch_type = BranchType.HOSTED

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.branch_puller = getUtility(IBranchPuller)
        # The absolute minimum value for any time field set to 'now'.
        self._now_minimum = self.getNow()

    def assertInFuture(self, time, delta):
        """Assert that 'time' is set (roughly) to 'now' + 'delta'.

        We do not want to assert that 'time' is exactly 'delta' in the future
        as this assertion is executing after whatever changed the value of
        'time'.
        """
        now_maximum = self.getNow()
        self.assertBetween(
            self._now_minimum + delta, time, now_maximum + delta)

    def getNow(self):
        """Return a datetime representing 'now' in UTC."""
        return datetime.now(pytz.timezone('UTC'))

    def makeAnyBranch(self):
        return self.factory.makeAnyBranch(branch_type=self.branch_type)

    def test_requestMirror(self):
        """requestMirror sets the mirror request time to 'now'."""
        branch = self.makeAnyBranch()
        branch.requestMirror()
        self.assertEqual(UTC_NOW, branch.next_mirror_time)

    def test_requestMirrorDuringPull(self):
        """Branches can have mirrors requested while they are being mirrored.
        If so, they should not be removed from the pull queue when the mirror
        is complete.
        """
        # We run these in separate transactions so as to have the times set to
        # different values. This is closer to what happens in production.
        branch = self.makeAnyBranch()
        branch.startMirroring()
        self.assertEqual(
            [], list(self.branch_puller.getPullQueue(branch.branch_type)))
        branch.requestMirror()
        self.assertEqual(
            [branch],
            list(self.branch_puller.getPullQueue(branch.branch_type)))
        next_mirror_time = branch.next_mirror_time
        branch.mirrorComplete('rev1')
        self.assertEqual(
            [branch],
            list(self.branch_puller.getPullQueue(branch.branch_type)))

    def test_startMirroringRemovesFromPullQueue(self):
        # Starting a mirror removes the branch from the pull queue.
        branch = self.makeAnyBranch()
        branch.requestMirror()
        self.assertEqual(
            set([branch]),
            set(self.branch_puller.getPullQueue(branch.branch_type)))
        branch.startMirroring()
        self.assertEqual(
            set(), set(self.branch_puller.getPullQueue(branch.branch_type)))

    def test_mirroringResetsMirrorRequest(self):
        """Mirroring branches resets their mirror request times."""
        branch = self.makeAnyBranch()
        branch.requestMirror()
        transaction.commit()
        branch.startMirroring()
        branch.mirrorComplete('rev1')
        self.assertEqual(None, branch.next_mirror_time)

    def test_mirrorFailureResetsMirrorRequest(self):
        """If a branch fails to mirror then update failures but don't mirror
        again until asked.
        """
        branch = self.makeAnyBranch()
        branch.requestMirror()
        branch.startMirroring()
        branch.mirrorFailed('No particular reason')
        self.assertEqual(1, branch.mirror_failures)
        self.assertEqual(None, branch.next_mirror_time)

    def test_pullQueueEmpty(self):
        """Branches with no next_mirror_time are not in the pull queue."""
        branch = self.makeAnyBranch()
        self.assertIs(None, branch.next_mirror_time)
        self.assertEqual(
            [], list(self.branch_puller.getPullQueue(self.branch_type)))

    def test_pastNextMirrorTimeInQueue(self):
        """Branches with next_mirror_time in the past are mirrored."""
        transaction.begin()
        branch = self.makeAnyBranch()
        branch.requestMirror()
        queue = self.branch_puller.getPullQueue(branch.branch_type)
        self.assertEqual([branch], list(queue))

    def test_futureNextMirrorTimeInQueue(self):
        """Branches with next_mirror_time in the future are not mirrored."""
        transaction.begin()
        branch = removeSecurityProxy(self.makeAnyBranch())
        tomorrow = self.getNow() + timedelta(1)
        branch.next_mirror_time = tomorrow
        branch.syncUpdate()
        transaction.commit()
        self.assertEqual(
            [], list(self.branch_puller.getPullQueue(branch.branch_type)))

    def test_pullQueueOrder(self):
        """Pull queue has the oldest mirror request times first."""
        branches = []
        for i in range(3):
            branch = removeSecurityProxy(self.makeAnyBranch())
            branch.next_mirror_time = self.getNow() - timedelta(hours=i+1)
            branch.sync()
            branches.append(branch)
        self.assertEqual(
            list(reversed(branches)),
            list(self.branch_puller.getPullQueue(self.branch_type)))


class TestMirroringForMirroredBranches(TestMirroringForHostedBranches):

    branch_type = BranchType.MIRRORED

    def setUp(self):
        TestMirroringForHostedBranches.setUp(self)
        branch_puller = getUtility(IBranchPuller)
        self.increment = branch_puller.MIRROR_TIME_INCREMENT
        self.max_failures = branch_puller.MAXIMUM_MIRROR_FAILURES

    def test_mirrorFailureResetsMirrorRequest(self):
        """If a branch fails to mirror then mirror again later."""
        branch = self.makeAnyBranch()
        branch.requestMirror()
        branch.startMirroring()
        branch.mirrorFailed('No particular reason')
        self.assertEqual(1, branch.mirror_failures)
        self.assertInFuture(branch.next_mirror_time, self.increment)

    def test_mirrorFailureBacksOffExponentially(self):
        """If a branch repeatedly fails to mirror then back off exponentially.
        """
        branch = self.makeAnyBranch()
        num_failures = 3
        for i in range(num_failures):
            branch.requestMirror()
            branch.startMirroring()
            branch.mirrorFailed('No particular reason')
        self.assertEqual(num_failures, branch.mirror_failures)
        self.assertInFuture(
            branch.next_mirror_time,
            (self.increment * 2 ** (num_failures - 1)))

    def test_repeatedMirrorFailuresDisablesMirroring(self):
        """If a branch's mirror failures exceed the maximum, disable
        mirroring.
        """
        branch = self.makeAnyBranch()
        for i in range(self.max_failures):
            branch.requestMirror()
            branch.startMirroring()
            branch.mirrorFailed('No particular reason')
        self.assertEqual(self.max_failures, branch.mirror_failures)
        self.assertEqual(None, branch.next_mirror_time)

    def test_mirroringResetsMirrorRequest(self):
        """Mirroring 'mirrored' branches sets their mirror request time to six
        hours in the future.
        """
        branch = self.makeAnyBranch()
        branch.requestMirror()
        transaction.commit()
        branch.startMirroring()
        branch.mirrorComplete('rev1')
        self.assertInFuture(branch.next_mirror_time, self.increment)
        self.assertEqual(0, branch.mirror_failures)


class TestMirroringForImportedBranches(TestMirroringForHostedBranches):

    branch_type = BranchType.IMPORTED


class TestRemoteBranches(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_raises_branch_type_error(self):
        # getPullQueue raises `BranchTypeError` if passed BranchType.REMOTE.
        # It's impossible to mirror remote branches, so we shouldn't even try.
        puller = getUtility(IBranchPuller)
        self.assertRaises(
            BranchTypeError, puller.getPullQueue, BranchType.REMOTE)


class AcquireBranchToPullTests:
    """Tests for acquiring branches to pull.

    The tests apply to branches accessed directly or through an XML-RPC style
    endpoint -- implement `assertNoBranchIsAquired`, `assertBranchIsAquired`
    and `startMirroring` as appropriate.
    """

    def assertNoBranchIsAquired(self):
        """XXX write me."""
        raise NotImplementedError(self.assertNoBranchIsAquired)

    def assertBranchIsAquired(self, branch):
        """XXX write me."""
        raise NotImplementedError(self.assertBranchIsAquired)

    def startMirroring(self, branch):
        """XXX write me."""
        raise NotImplementedError(self.startMirroring)

    def test_empty(self):
        # If there is no branch that needs pulling, acquireBranchToPull
        # returns None.
        self.assertNoBranchIsAquired()

    def test_simple(self):
        # If there is one branch that needs mirroring, acquireBranchToPull
        # returns that.
        branch = self.factory.makeAnyBranch()
        branch.requestMirror()
        self.assertBranchIsAquired(branch)

    def test_no_inprogress(self):
        # If a branch is being mirrored, it is not returned.
        branch = self.factory.makeAnyBranch()
        branch.requestMirror()
        self.startMirroring(branch)
        self.assertNoBranchIsAquired()

    def test_first_requested_returned(self):
        # If two branches are to be mirrored, the one that was requested first
        # is returned.
        first_branch = self.factory.makeAnyBranch()
        # You can only request a mirror now, so to pretend that we requested
        # it some time ago, we cheat with removeSecurityProxy().
        first_branch.requestMirror()
        naked_first_branch = removeSecurityProxy(first_branch)
        naked_first_branch.next_mirror_time -= timedelta(seconds=100)
        second_branch = self.factory.makeAnyBranch()
        second_branch.requestMirror()
        naked_second_branch = removeSecurityProxy(second_branch)
        naked_second_branch.next_mirror_time -= timedelta(seconds=50)
        self.assertBranchIsAquired(naked_first_branch)


class TestAcquireBranchToPullDirectly(TestCaseWithFactory,
                                      AcquireBranchToPullTests):
    """Direct tests for `IBranchPuller.acquireBranchToPull`."""

    layer = DatabaseFunctionalLayer

    def assertNoBranchIsAquired(self):
        """See `AcquireBranchToPullTests`."""
        acquired_branch = getUtility(IBranchPuller).acquireBranchToPull()
        self.assertEqual(None, acquired_branch)

    def assertBranchIsAquired(self, branch):
        """See `AcquireBranchToPullTests`."""
        acquired_branch = getUtility(IBranchPuller).acquireBranchToPull()
        self.assertEqual(branch, acquired_branch)
        self.assertIsNot(None, acquired_branch.last_mirror_attempt)
        self.assertIs(None, acquired_branch.next_mirror_time)

    def startMirroring(self, branch):
        """See `AcquireBranchToPullTests`."""
        branch.startMirroring()



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

