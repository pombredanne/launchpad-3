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


class BranchVisibilityPolicyTestCase(TestCaseWithFactory):
    """Base class for tests to make testing of branch visibility easier."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Setup some sample people and teams.

        The team names are: "xray", "yankee", and "zulu".

        The people are:

          * "albert", who is a member of all three teams.
          * "bob", who is a member of yankee.
          * "charlie", who is a member of zulu.
          * "doug", who is a member of no teams.
        """
        TestCaseWithFactory.setUp(self, 'admin@canonical.com')
        # Our test product.
        person_set = getUtility(IPersonSet)
        self.product = self.factory.makeProduct()
        # Create some test people.
        self.albert, alberts_email = person_set.createPersonAndEmail(
            'albert@code.ninja.nz', PersonCreationRationale.USER_CREATED,
            name='albert', displayname='Albert Tester')
        self.albert.setPreferredEmail(alberts_email)
        self.bob, ignored  = person_set.createPersonAndEmail(
            'bob@code.ninja.nz', PersonCreationRationale.USER_CREATED,
            name='bob', displayname='Bob Tester')
        self.charlie, ignored  = person_set.createPersonAndEmail(
            'charlie@code.ninja.nz', PersonCreationRationale.USER_CREATED,
            name='charlie', displayname='Charlie Tester')
        self.doug, ignored  = person_set.createPersonAndEmail(
            'doug@code.ninja.nz', PersonCreationRationale.USER_CREATED,
            name='doug', displayname='Doug Tester')

        self.people = (self.albert, self.bob, self.charlie, self.doug)

        # And create some test teams.
        self.xray = person_set.newTeam(
            self.albert, 'xray', 'Xray Team',
            subscriptionpolicy=TeamSubscriptionPolicy.OPEN)
        self.yankee = person_set.newTeam(
            self.albert, 'yankee', 'Yankee Team',
            subscriptionpolicy=TeamSubscriptionPolicy.OPEN)
        self.zulu = person_set.newTeam(
            self.albert, 'zulu', 'Zulu Team',
            subscriptionpolicy=TeamSubscriptionPolicy.OPEN)
        self.teams = (self.xray, self.yankee, self.zulu)

        # Set the memberships of our test people to the test teams.
        self.albert.join(self.xray)
        self.albert.join(self.yankee)
        self.albert.join(self.zulu)
        self.bob.join(self.yankee)
        self.charlie.join(self.zulu)

    def defineTeamPolicies(self, team_policies):
        """Shortcut to help define team policies."""
        for team, rule in team_policies:
            self.product.setBranchVisibilityTeamPolicy(team, rule)

    def assertBranchRule(self, registrant, owner, expected_rule):
        """Check the getBranchVisibilityRuleForBranch results for a branch."""
        branch = self.factory.makeProductBranch(
            registrant=registrant, owner=owner, product=self.product)
        rule = self.product.getBranchVisibilityRuleForBranch(branch)
        self.assertEqual(rule, expected_rule,
                         'Wrong visibililty rule returned: '
                         'expected %s, got %s'
                         % (expected_rule.name, rule.name))

    def assertPublic(self, creator, owner):
        """Assert that the policy check would result in a public branch.

        :param creator: The user creating the branch.
        :param owner: The person or team that will be the owner of the branch.
        """
        namespace = get_branch_namespace(owner, product=self.product)
        self.assertFalse(namespace.areNewBranchesPrivate())

    def assertPrivateSubscriber(self, creator, owner, subscriber):
        """Assert that the policy check results in a private branch.

        :param creator: The user creating the branch.
        :param owner: The person or team that will be the owner of the branch.
        :param subscriber: The expected implicit subscriber to the branch.
        """
        namespace = get_branch_namespace(owner, product=self.product)
        self.assertTrue(namespace.areNewBranchesPrivate())
        if subscriber is None:
            self.assertIs(None, namespace.getPrivacySubscriber())
        else:
            self.assertEqual(subscriber, namespace.getPrivacySubscriber())

    def assertPolicyCheckRaises(self, error, creator, owner):
        """Assert that the policy check raises an exception.

        :param error: The exception class that should be raised.
        :param creator: The user creating the branch.
        :param owner: The person or team that will be the owner of the branch.
        """
        namespace = get_branch_namespace(owner, product=self.product)
        self.assertRaises(
            error,
            namespace.validateNewBranch,
            registrant=creator, name=self.factory.getUniqueString())


class TestTeamMembership(BranchVisibilityPolicyTestCase):
    """Assert the expected team memberhsip of the test users."""

    def test_team_memberships(self):
        albert, bob, charlie, doug = self.people
        xray, yankee, zulu = self.teams
        # Albert is a member of all three teams.
        self.failUnless(albert.inTeam(xray),
                        "Albert should be in team Xray team.")
        self.failUnless(albert.inTeam(yankee),
                        "Albert should be in the Yankee.")
        self.failUnless(albert.inTeam(zulu),
                        "Albert should be in Zulu team.")
        # Bob is a member of only Yankee.
        self.failIf(bob.inTeam(xray),
                    "Bob should not be in team Xray team.")
        self.failUnless(bob.inTeam(yankee),
                        "Bob should be in the Yankee team.")
        self.failIf(bob.inTeam(zulu),
                    "Bob should not be in the Zulu team.")
        # Charlie is a member of only Zulu.
        self.failIf(charlie.inTeam(xray),
                    "Charlie should not be in team Xray team.")
        self.failIf(charlie.inTeam(yankee),
                    "Charlie should not be in the Yankee team.")
        self.failUnless(charlie.inTeam(zulu),
                        "Charlie should be in the Zulu team.")
        # Doug is not a member of any
        self.failIf(doug.inTeam(xray),
                    "Doug should not be in team Xray team.")
        self.failIf(doug.inTeam(yankee),
                    "Doug should not be in the Yankee team.")
        self.failIf(doug.inTeam(zulu),
                    "Doug should not be in the Zulu team.")


class NoPolicies(BranchVisibilityPolicyTestCase):
    """Test behaviour with no team policies defined."""

    def test_creation_where_not_team_member(self):
        """If the creator isn't a member of the owner an exception is raised.
        """
        self.assertPolicyCheckRaises(
            BranchCreatorNotMemberOfOwnerTeam, self.doug, self.xray)

    def test_creation_under_different_user(self):
        """If the owner is a user other than the creator an exception is
        raised.
        """
        self.assertPolicyCheckRaises(
            BranchCreatorNotOwner, self.albert, self.bob)

    def test_public_branch_creation(self):
        """Branches where the creator is a memeber of owner will be public."""
        albert, bob, charlie, doug = self.people
        xray, yankee, zulu = self.teams

        self.assertPublic(albert, albert)
        self.assertPublic(albert, xray)
        self.assertPublic(albert, yankee)
        self.assertPublic(albert, zulu)

        self.assertPublic(bob, bob)
        self.assertPublic(bob, yankee)

        self.assertPublic(charlie, charlie)
        self.assertPublic(charlie, zulu)

        self.assertPublic(doug, doug)


class PolicySimple(BranchVisibilityPolicyTestCase):
    """Test the visiblity policy where the base visibility rule is PUBLIC with
    one team specified to have PRIVATE branches.
    """

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self.defineTeamPolicies((
            (None, BranchVisibilityRule.PUBLIC),
            (self.xray, BranchVisibilityRule.PRIVATE),
            ))

    def test_xray_branches_private(self):
        """Branches created in the xray namespace will be private."""
        self.assertPrivateSubscriber(self.albert, self.xray, None)

    def test_xray_member_branches_private(self):
        """Branches created by members of the Xray team in their own namespace
        will be private with the Xray team subscribed.
        """
        self.assertPrivateSubscriber(self.albert, self.albert, self.xray)

    def test_xray_member_other_namespace_public(self):
        """Branches created by members of the Xray team in other team
        namespaces are public.
        """
        self.assertPublic(self.albert, self.yankee)
        self.assertPublic(self.albert, self.zulu)

    def test_public_branches(self):
        """Branches created by users not in team Xray are created as public
        branches.
        """
        albert, bob, charlie, doug = self.people
        xray, yankee, zulu = self.teams

        self.assertPublic(bob, bob)
        self.assertPublic(bob, yankee)

        self.assertPublic(charlie, charlie)
        self.assertPublic(charlie, zulu)

        self.assertPublic(doug, doug)


class PolicyPrivateOnly(BranchVisibilityPolicyTestCase):
    """Test the visiblity policy where the base visibility rule is PUBLIC with
    one team specified to have the PRIVATE_ONLY rule.

    PRIVATE_ONLY only stops the user from changing the branch from private to
    public and for branch creation behaves in the same maner as the PRIVATE
    policy.
    """

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self.defineTeamPolicies((
            (None, BranchVisibilityRule.PUBLIC),
            (self.xray, BranchVisibilityRule.PRIVATE_ONLY),
            ))

    def test_xray_branches_private(self):
        """Branches created in the xray namespace will be private."""
        self.assertPrivateSubscriber(self.albert, self.xray, None)

    def test_xray_member_branches_private(self):
        """Branches created by members of the Xray team in their own namespace
        will be private with the Xray team subscribed.
        """
        self.assertPrivateSubscriber(self.albert, self.albert, self.xray)

    def test_xray_member_other_namespace_public(self):
        """Branches created by members of the Xray team in other team
        namespaces are public.
        """
        self.assertPublic(self.albert, self.yankee)
        self.assertPublic(self.albert, self.zulu)

    def test_public_branches(self):
        """Branches created by users not in team Xray are created as public
        branches.
        """
        albert, bob, charlie, doug = self.people
        xray, yankee, zulu = self.teams

        self.assertPublic(bob, bob)
        self.assertPublic(bob, yankee)

        self.assertPublic(charlie, charlie)
        self.assertPublic(charlie, zulu)

        self.assertPublic(doug, doug)


class PolicyForbidden(BranchVisibilityPolicyTestCase):
    """Test the visiblity policy where the base visibility rule is FORBIDDEN
    with one team specified to have the PRIVATE branches and another team
    specified to have PUBLIC branches.
    """

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self.defineTeamPolicies((
            (None, BranchVisibilityRule.FORBIDDEN),
            (self.xray, BranchVisibilityRule.PRIVATE),
            (self.yankee, BranchVisibilityRule.PUBLIC),
            ))

    def test_rule_for_branch_most_specific(self):
        """Since Albert is in both xray and yankee, the PRIVATE rule is
        returned in preference to the PUBLIC one.
        """
        self.assertBranchRule(
            self.albert, self.albert, BranchVisibilityRule.PRIVATE)

    def test_rule_for_branch_exact_defined(self):
        """Branches in the yankee namespace will return the PUBLIC rule as it
        is defined for the branch owner.
        """
        self.assertBranchRule(
            self.albert, self.yankee, BranchVisibilityRule.PUBLIC)

    def test_branch_creation_forbidden_non_members(self):
        """People who are not members of Xray or Yankee are not allowed to
        create branches.
        """
        self.assertPolicyCheckRaises(
            BranchCreationForbidden, self.charlie, self.charlie)
        self.assertPolicyCheckRaises(
            BranchCreationForbidden, self.charlie, self.zulu)

        self.assertPolicyCheckRaises(
            BranchCreationForbidden, self.doug, self.doug)

    def test_branch_creation_forbidden_other_namespace(self):
        """People who are members of Xray or Yankee are not allowed to
        create branches in a namespace of a team that is not a member
        of Xray or Yankee.
        """
        self.assertPolicyCheckRaises(
            BranchCreationForbidden, self.albert, self.zulu)

    def test_yankee_branches_public(self):
        """Branches in the yankee namespace are public."""
        self.assertPublic(self.bob, self.yankee)
        self.assertPublic(self.albert, self.yankee)

    def test_yankee_member_branches_public(self):
        """Branches created by a member of Yankee, who is not a member
        of Xray will be public.
        """
        self.assertPublic(self.bob, self.bob)

    def test_xray_branches_private(self):
        """Branches in the xray namespace will be private."""
        self.assertPrivateSubscriber(self.albert, self.xray, None)

    def test_xray_member_branches_private(self):
        """Branches created by Xray team members in their own namespace
        will be private, and subscribed to by the Xray team.
        """
        self.assertPrivateSubscriber(self.albert, self.albert, self.xray)


class PolicyTeamPrivateOverlap(BranchVisibilityPolicyTestCase):
    """Test the visibility policy where a user is a member of multiple teams
    with PRIVATE branches enabled.
    """

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self.defineTeamPolicies((
            (self.xray, BranchVisibilityRule.PRIVATE),
            (self.zulu, BranchVisibilityRule.PRIVATE),
            ))

    def test_public_branches_for_non_members(self):
        """Branches created by people who are not members of xray or zulu
        will be public branches.
        """
        self.assertPublic(self.bob, self.bob)
        self.assertPublic(self.bob, self.yankee)
        self.assertPublic(self.doug, self.doug)

    def test_public_branches_for_members_in_other_namespace(self):
        """If a member of xray or zulu creates a branch for a team that is
        not a member of xray or zulu, then the branch will be a public branch.
        """
        self.assertPublic(self.albert, self.yankee)

    def test_team_branches_private(self):
        """Branches created in the namespace of a team that has private
        branches specified are private.
        """
        self.assertPrivateSubscriber(self.charlie, self.zulu, None)
        self.assertPrivateSubscriber(self.albert, self.zulu, None)
        self.assertPrivateSubscriber(self.albert, self.xray, None)

    def test_one_membership_private_with_subscriber(self):
        """If the creator of the branch is a member of only one team that has
        private branches set up, then that team will be subscribed to any
        branches that the creator registers in their own namespace.
        """
        self.assertPrivateSubscriber(self.charlie, self.charlie, self.zulu)

    def test_two_memberships_private_no_subscriber(self):
        """If the creator of the branch is a member of two or more teams
        that have private branches enabled, then when a branch is created
        in their own namespace, there are no implicit subscribers.

        This is done as we cannot guess which team should have access
        to the private branch.
        """
        self.assertPrivateSubscriber(self.albert, self.albert, None)


class ComplexPolicyStructure(BranchVisibilityPolicyTestCase):
    """Test the visibility policy with a complex policy structure.

    The base visibility policy is set to FORBIDDEN, with both xray and yankee
    teams creating PRIVATE branches.  Members of zulu team create PUBLIC
    branches.

    Branch creation is forbidden to all people who are not a member of
    one of the teams: xray, yankee or zulu.  Members of zulu can create
    branches that are public.  Branches created by members of xray and
    yankee in the team namespace are private, and branches created in the
    namespace of the user are also created private.
    """

    def setUp(self):
        BranchVisibilityPolicyTestCase.setUp(self)
        self.defineTeamPolicies((
            (None, BranchVisibilityRule.FORBIDDEN),
            (self.xray, BranchVisibilityRule.PRIVATE),
            (self.yankee, BranchVisibilityRule.PRIVATE_ONLY),
            (self.zulu, BranchVisibilityRule.PUBLIC),
            ))

    def test_rule_for_branch_most_specific(self):
        """Since Albert is in both xray and yankee, the PRIVATE_ONLY rule is
        returned in preference to the PUBLIC or PRIVATE one.
        """
        self.assertBranchRule(
            self.albert, self.albert, BranchVisibilityRule.PRIVATE_ONLY)

    def test_rule_for_branch_exact_defined(self):
        """Branches in the zulu namespace will return the PUBLIC rule as it is
        defined for the branch owner.
        """
        self.assertBranchRule(
            self.albert, self.xray, BranchVisibilityRule.PRIVATE)
        self.assertBranchRule(
            self.albert, self.yankee, BranchVisibilityRule.PRIVATE_ONLY)
        self.assertBranchRule(
            self.albert, self.zulu, BranchVisibilityRule.PUBLIC)

    def test_non_membership_cannot_create_branches(self):
        """A user who is not a member of any specified team gets the
        base policy, which is in this case FORBIDDEN.
        """
        self.assertPolicyCheckRaises(
            BranchCreationForbidden, self.doug, self.doug)

    def test_zulu_branches_public(self):
        """Branches pushed to the zulu team namespace are public branches."""
        self.assertPublic(self.albert, self.zulu)
        self.assertPublic(self.charlie, self.zulu)

    def test_zulu_members_only_public(self):
        """A user who is a member of zulu, and not a member of a team that
        specifies private branch creation have public branches when created
        in the user's own namespace.
        """
        self.assertPublic(self.charlie, self.charlie)

    def test_xray_and_yankee_branches_private(self):
        """Branches that are created in the namespace of either xray or yankee
        are private branches.
        """
        self.assertPrivateSubscriber(self.albert, self.xray, None)
        self.assertPrivateSubscriber(self.albert, self.yankee, None)
        self.assertPrivateSubscriber(self.bob, self.yankee, None)

    def test_xray_member_private_with_subscription(self):
        """Branches created by a user who is a member of only one team that
        specifies private branches will have branches in the user's namespace
        created as private branches with the team subscribed to them.
        """
        self.assertPrivateSubscriber(self.bob, self.bob, self.yankee)

    def test_multiple_memberships_private(self):
        """If the user is a member of multiple teams that specify private
        branches, then this overrides PUBLIC policy that may apply.

        Any branch created in the user's own namespace will not have any
        implicit subscribers.
        """
        self.assertPrivateSubscriber(self.albert, self.albert, None)


class TeamsWithinTeamsPolicies(BranchVisibilityPolicyTestCase):
    """Test the visibility policy when teams within teams have different
    visibility rules.
    """

    def setUp(self):
        """Join up the teams so zulu is in yankee, and yankee is in xray."""
        BranchVisibilityPolicyTestCase.setUp(self)
        login("foo.bar@canonical.com")
        self.yankee.addMember(self.zulu, self.albert, force_team_add=True)
        self.xray.addMember(self.yankee, self.albert, force_team_add=True)
        self.defineTeamPolicies((
            (None, BranchVisibilityRule.FORBIDDEN),
            (self.xray, BranchVisibilityRule.PRIVATE),
            (self.yankee, BranchVisibilityRule.PUBLIC),
            (self.zulu, BranchVisibilityRule.PRIVATE),
            ))

    def test_team_memberships(self):
        albert, bob, charlie, doug = self.people
        xray, yankee, zulu = self.teams
        # Albert is a member of all three teams.
        self.failUnless(albert.inTeam(xray),
                        "Albert should be in team Xray team.")
        self.failUnless(albert.inTeam(yankee),
                        "Albert should be in the Yankee.")
        self.failUnless(albert.inTeam(zulu),
                        "Albert should be in Zulu team.")
        # Bob is a member of Yankee, and now Xray.
        self.failUnless(bob.inTeam(xray),
                        "Bob should now be in team Xray team.")
        self.failUnless(bob.inTeam(yankee),
                        "Bob should be in the Yankee team.")
        self.failIf(bob.inTeam(zulu),
                    "Bob should not be in the Zulu team.")
        # Charlie is a member of Zulu, and through Zulu a member
        # of Yankee, and through Yankee a member of Xray.
        self.failUnless(charlie.inTeam(xray),
                        "Charlie should now be in team Xray team.")
        self.failUnless(charlie.inTeam(yankee),
                        "Charlie should now be in the Yankee team.")
        self.failUnless(charlie.inTeam(zulu),
                        "Charlie should be in the Zulu team.")
        # Doug is not a member of any
        self.failIf(doug.inTeam(xray),
                    "Doug should not be in team Xray team.")
        self.failIf(doug.inTeam(yankee),
                    "Doug should not be in the Yankee team.")
        self.failIf(doug.inTeam(zulu),
                    "Doug should not be in the Zulu team.")

    def test_non_membership_cannot_create_branches(self):
        """A user who is not a member of any specified team gets the
        base policy, which is in this case FORBIDDEN.
        """
        self.assertPolicyCheckRaises(
            BranchCreationForbidden, self.doug, self.doug)

    def test_xray_and_zulu_branches_private_no_subscriber(self):
        """All branches created in the namespace of teams that specify
        private branches are private with no subscribers.
        """
        self.assertPrivateSubscriber(self.albert, self.xray, None)
        self.assertPrivateSubscriber(self.bob, self.xray, None)
        self.assertPrivateSubscriber(self.charlie, self.xray, None)

        self.assertPrivateSubscriber(self.albert, self.zulu, None)
        self.assertPrivateSubscriber(self.charlie, self.zulu, None)

    def test_yankee_branches_public(self):
        """All branches created in the namespace of teams that specify
        public branches are public.
        """
        self.assertPublic(self.albert, self.yankee)
        self.assertPublic(self.bob, self.yankee)
        self.assertPublic(self.charlie, self.yankee)

    def test_privacy_through_team_membership_of_private_team(self):
        """Policies that apply to team apply to people that are members
        indirectly in the same way as direct membership.
        """
        self.assertPrivateSubscriber(self.bob, self.bob, self.xray)

    def test_multiple_private_policies_through_indirect_membership(self):
        """If a person is a member of a team that specifies private branches,
        and that team is also a member either directly or indirectly of
        another team that specifies private branches, then when members of
        those teams create branches, those branches have no implicit
        subscribers.
        """
        self.assertPrivateSubscriber(self.albert, self.albert, None)
        self.assertPrivateSubscriber(self.charlie, self.charlie, None)


class JunkBranches(BranchVisibilityPolicyTestCase):
    """Branches are considered junk if they have no associated product.
    It is the product that has the branch visibility policy, so junk branches
    have no related visibility policy."""

    def setUp(self):
        """Override the product used for the visibility checks."""
        BranchVisibilityPolicyTestCase.setUp(self)
        # Override the product that is used in the check tests.
        self.product = None

    def test_junk_branches_public(self):
        """Branches created by anyone that has no product defined are created
        as public branches.
        """
        self.assertPublic(self.albert, self.albert)

    def test_team_junk_branches(self):
        """Team junk branches are allowed, and are public."""
        self.assertPublic(self.albert, self.xray)

    def test_no_create_junk_branch_for_other_user(self):
        """One user can't create +junk branches owned by another."""
        self.assertPolicyCheckRaises(
            BranchCreatorNotOwner, self.albert, self.doug)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
