# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for BranchSet."""

__metaclass__ = type

from datetime import datetime, timedelta
from unittest import TestCase, TestLoader

import pytz

import transaction

from canonical.database.constants import UTC_NOW

from canonical.launchpad.ftests import login, logout, ANONYMOUS, syncUpdate
from canonical.launchpad.database.branch import BranchSet
from canonical.launchpad.interfaces import (
    BranchCreationForbidden, BranchCreationNoTeamOwnedJunkBranches,
    BranchCreatorNotMemberOfOwnerTeam, BranchCreatorNotOwner,
    BranchLifecycleStatus, BranchType, BranchVisibilityRule, IBranchSet,
    IPersonSet, IProductSet, MAXIMUM_MIRROR_FAILURES, MIRROR_TIME_INCREMENT,
    PersonCreationRationale, TeamSubscriptionPolicy)
from canonical.launchpad.interfaces.branchnamespace import (
    get_branch_namespace)
from canonical.launchpad.testing import (
    LaunchpadObjectFactory, TestCaseWithFactory)
from canonical.launchpad.validators import LaunchpadValidationError

from canonical.testing import DatabaseFunctionalLayer

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy


class TestBranchSet(TestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCase.setUp(self)
        login(ANONYMOUS)
        self.product = getUtility(IProductSet).getByName('firefox')
        self.branch_set = BranchSet()

    def tearDown(self):
        logout()
        TestCase.tearDown(self)

    def test_limitedByQuantity(self):
        """When getting the latest branches for a product, we can specify the
        maximum number of branches we want to know about.
        """
        quantity = 3
        latest_branches = self.branch_set.getLatestBranchesForProduct(
            self.product, quantity)
        self.assertEqual(quantity, len(list(latest_branches)))

    def test_onlyForProduct(self):
        """getLatestBranchesForProduct returns branches only from the
        requested product.
        """
        quantity = 5
        latest_branches = self.branch_set.getLatestBranchesForProduct(
            self.product, quantity)
        self.assertEqual(
            [self.product.name] * quantity,
            [branch.product.name for branch in latest_branches])

    def test_abandonedBranchesNotIncluded(self):
        """getLatestBranchesForProduct does not include branches that have
        been abandoned, because they are not relevant for those interested
        in recent activity.
        """
        original_branches = list(
            self.branch_set.getLatestBranchesForProduct(self.product, 5))
        branch = original_branches[0]
        # XXX: JonathanLange 2007-07-06: WHITEBOXING. The anonymous user
        # cannot change branch details, so we remove the security proxy and
        # change it.
        branch = removeSecurityProxy(branch)
        branch.lifecycle_status = BranchLifecycleStatus.ABANDONED
        syncUpdate(branch)
        latest_branches = list(
            self.branch_set.getLatestBranchesForProduct(self.product, 5))
        self.assertEqual(original_branches[1:], latest_branches)


class TestBranchSetNew(TestCaseWithFactory):
    """Tests for BranchSet.new()."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        # This person should be considered to be wholly arbitrary.
        self.person = self.factory.makePerson()
        assert self.person is not None, "Sample Person not found."
        self.branch_set = getUtility(IBranchSet)

    def makeNewBranchWithName(self, name):
        """Attempt to create a new branch with name 'name'.

        It will a +junk branch owned and authored by Sample Person, but this
        shouldn't be important.
        """
        return self.branch_set.new(
            BranchType.HOSTED, name, self.person, self.person, None, None)

    def test_permitted_first_character(self):
        # The first character of a branch name must be a letter or a number.
        for c in [chr(i) for i in range(128)]:
            if c.isalnum():
                self.makeNewBranchWithName(c)
            else:
                self.assertRaises(
                    LaunchpadValidationError, self.makeNewBranchWithName, c)

    def test_permitted_subsequent_character(self):
        # After the first character, letters, numbers and certain punctuation
        # is permitted.
        for c in [chr(i) for i in range(128)]:
            if c.isalnum() or c in '+-_@.':
                self.makeNewBranchWithName('a' + c)
            else:
                self.assertRaises(
                    LaunchpadValidationError,
                    self.makeNewBranchWithName, 'a' + c)

    def test_source_package_branch(self):
        distroseries = self.factory.makeDistroRelease()
        sourcepackagename = self.factory.makeSourcePackageName()
        owner = self.factory.makePerson()
        new_branch = self.branch_set.new(
            BranchType.HOSTED, name=self.factory.getUniqueString(),
            registrant=owner, owner=owner, product=None, url=None,
            distroseries=distroseries, sourcepackagename=sourcepackagename)
        self.assertEqual(distroseries, new_branch.distroseries)
        self.assertEqual(sourcepackagename, new_branch.sourcepackagename)
        self.assertIs(None, new_branch.product)


class TestMirroringForHostedBranches(TestCaseWithFactory):
    """Tests for mirroring methods of a branch."""

    layer = DatabaseFunctionalLayer
    branch_type = BranchType.HOSTED

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.branch_set = getUtility(IBranchSet)
        # The absolute minimum value for any time field set to 'now'.
        self._now_minimum = self.getNow()

    def assertBetween(self, lower_bound, variable, upper_bound):
        """Assert that 'variable' is strictly between two boundaries."""
        self.assertTrue(
            lower_bound < variable < upper_bound,
            "%r < %r < %r" % (lower_bound, variable, upper_bound))

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
        transaction.commit()
        branch.requestMirror()
        removeSecurityProxy(branch).sync()
        self.assertNotEqual(
            branch.last_mirror_attempt, branch.next_mirror_time)
        next_mirror_time = branch.next_mirror_time
        branch.mirrorComplete('rev1')
        self.assertEqual(next_mirror_time, branch.next_mirror_time)

    def test_startMirroringRemovesFromPullQueue(self):
        # Starting a mirror removes the branch from the pull queue.
        branch = self.makeAnyBranch()
        branch.requestMirror()
        self.assertEqual(
            set([branch]),
            set(self.branch_set.getPullQueue(branch.branch_type)))
        branch.startMirroring()
        self.assertEqual(
            set(), set(self.branch_set.getPullQueue(branch.branch_type)))

    def test_mirrorCompleteRemovesFromPullQueue(self):
        """Completing the mirror removes the branch from the pull queue."""
        branch = self.makeAnyBranch()
        branch.requestMirror()
        branch.startMirroring()
        branch.mirrorComplete('rev1')
        self.assertEqual(
            [], list(self.branch_set.getPullQueue(branch.branch_type)))

    def test_mirroringResetsMirrorRequest(self):
        """Mirroring branches resets their mirror request times."""
        branch = self.makeAnyBranch()
        branch.requestMirror()
        transaction.commit()
        branch.startMirroring()
        branch.mirrorComplete('rev1')
        self.assertEqual(None, branch.next_mirror_time)

    def test_mirroringResetsMirrorRequestBackwardsCompatibility(self):
        # Mirroring branches resets their mirror request times. Before
        # 2008-09-10, startMirroring would leave next_mirror_time untouched,
        # and mirrorComplete reset the next_mirror_time based on the old
        # value. This test confirms that branches which were in the middle of
        # mirroring during the upgrade will have their next_mirror_time set
        # properly eventually. This test can be removed after the 2.1.9
        # release.
        branch = self.makeAnyBranch()
        # Set next_mirror_time to NOW, putting the branch in the pull queue.
        branch.requestMirror()
        next_mirror_time = branch.next_mirror_time
        # In the new code, startMirroring sets next_mirror_time to None...
        branch.startMirroring()
        # ... so we make it behave like the old code by restoring the previous
        # value. This simulates a branch that was in the middle of mirroring
        # during the 2.1.9 upgrade.
        removeSecurityProxy(branch).next_mirror_time = next_mirror_time
        branch.mirrorComplete('rev1')
        # Even though the mirror is complete, the branch is still in the pull
        # queue. This is not normal behaviour.
        self.assertIn(
            branch, self.branch_set.getPullQueue(branch.branch_type))
        # But on the next mirror, everything is OK, since startMirroring does
        # the right thing.
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
        self.assertEqual(
            [], list(self.branch_set.getPullQueue(self.branch_type)))

    def test_pastNextMirrorTimeInQueue(self):
        """Branches with next_mirror_time in the past are mirrored."""
        transaction.begin()
        branch = self.makeAnyBranch()
        branch.requestMirror()
        branch_id = branch.id
        transaction.commit()
        self.assertEqual(
            [branch_id],
            [branch.id
             for branch in self.branch_set.getPullQueue(branch.branch_type)])

    def test_futureNextMirrorTimeInQueue(self):
        """Branches with next_mirror_time in the future are not mirrored."""
        transaction.begin()
        branch = removeSecurityProxy(self.makeAnyBranch())
        tomorrow = self.getNow() + timedelta(1)
        branch.next_mirror_time = tomorrow
        branch.syncUpdate()
        transaction.commit()
        self.assertEqual(
            [], list(self.branch_set.getPullQueue(branch.branch_type)))

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
            list(self.branch_set.getPullQueue(self.branch_type)))


class TestMirroringForMirroredBranches(TestMirroringForHostedBranches):

    branch_type = BranchType.MIRRORED

    def test_mirrorFailureResetsMirrorRequest(self):
        """If a branch fails to mirror then mirror again later."""
        branch = self.makeAnyBranch()
        branch.requestMirror()
        branch.startMirroring()
        branch.mirrorFailed('No particular reason')
        self.assertEqual(1, branch.mirror_failures)
        self.assertInFuture(branch.next_mirror_time, MIRROR_TIME_INCREMENT)

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
            (MIRROR_TIME_INCREMENT * 2 ** (num_failures - 1)))

    def test_repeatedMirrorFailuresDisablesMirroring(self):
        """If a branch's mirror failures exceed the maximum, disable
        mirroring.
        """
        branch = self.makeAnyBranch()
        for i in range(MAXIMUM_MIRROR_FAILURES):
            branch.requestMirror()
            branch.startMirroring()
            branch.mirrorFailed('No particular reason')
        self.assertEqual(MAXIMUM_MIRROR_FAILURES, branch.mirror_failures)
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
        self.assertInFuture(
            branch.next_mirror_time, MIRROR_TIME_INCREMENT)
        self.assertEqual(0, branch.mirror_failures)

    def test_mirroringResetsMirrorRequestBackwardsCompatibility(self):
        # Mirroring branches resets their mirror request times. Before
        # 2008-09-10, startMirroring would leave next_mirror_time untouched,
        # and mirrorComplete reset the next_mirror_time based on the old
        # value. This test confirms that branches which were in the middle of
        # mirroring during the upgrade will have their next_mirror_time set
        # properly eventually.
        branch = self.makeAnyBranch()
        # Set next_mirror_time to NOW, putting the branch in the pull queue.
        branch.requestMirror()
        next_mirror_time = branch.next_mirror_time
        # In the new code, startMirroring sets next_mirror_time to None...
        branch.startMirroring()
        # ... so we make it behave like the old code by restoring the previous
        # value. This simulates a branch that was in the middle of mirroring
        # during the 2.1.9 upgrade.
        removeSecurityProxy(branch).next_mirror_time = next_mirror_time
        branch.mirrorComplete('rev1')
        # Even though the mirror is complete, the branch is still in the pull
        # queue. This is not normal behaviour.
        self.assertIn(
            branch, self.branch_set.getPullQueue(branch.branch_type))
        # But on the next mirror, everything is OK, since startMirroring does
        # the right thing.
        branch.startMirroring()
        branch.mirrorComplete('rev1')
        self.assertInFuture(
            branch.next_mirror_time, MIRROR_TIME_INCREMENT)


class TestMirroringForImportedBranches(TestMirroringForHostedBranches):

    branch_type = BranchType.IMPORTED


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
