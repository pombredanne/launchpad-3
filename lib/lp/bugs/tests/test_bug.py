
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.bugs.model.Bug."""

__metaclass__ = type

from lazr.lifecycle.snapshot import Snapshot
from zope.component import getUtility
from zope.interface import providedBy
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import DatabaseFunctionalLayer

from lp.bugs.enum import BugNotificationLevel
from lp.bugs.interfaces.bug import(
    CreateBugParams,
    IBugSet,
    )
from lp.bugs.interfaces.bugtask import (
    BugTaskImportance,
    BugTaskStatus,
    UserCannotEditBugTaskAssignee,
    UserCannotEditBugTaskImportance,
    UserCannotEditBugTaskMilestone,
    )
from lp.registry.interfaces.accesspolicy import UnsuitableAccessPolicyError
from lp.testing import (
    person_logged_in,
    StormStatementRecorder,
    TestCaseWithFactory,
    )


class TestBugSubscriptionMethods(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSubscriptionMethods, self).setUp()
        self.bug = self.factory.makeBug()
        self.person = self.factory.makePerson()

    def test_is_muted_returns_true_for_muted_users(self):
        # Bug.isMuted() will return True if the person passed to it is muted.
        with person_logged_in(self.person):
            self.bug.mute(self.person, self.person)
            self.assertEqual(True, self.bug.isMuted(self.person))

    def test_is_muted_returns_false_for_direct_subscribers(self):
        # Bug.isMuted() will return False if the user has a
        # regular subscription.
        with person_logged_in(self.person):
            self.bug.subscribe(
                self.person, self.person, level=BugNotificationLevel.METADATA)
            self.assertEqual(False, self.bug.isMuted(self.person))

    def test_is_muted_returns_false_for_non_subscribers(self):
        # Bug.isMuted() will return False if the user has no
        # subscription.
        with person_logged_in(self.person):
            self.assertEqual(False, self.bug.isMuted(self.person))

    def test_mute_team_fails(self):
        # Muting a subscription for an entire team doesn't work.
        with person_logged_in(self.person):
            team = self.factory.makeTeam(owner=self.person)
            self.assertRaises(AssertionError,
                              self.bug.mute, team, team)

    def test_mute_mutes_user(self):
        # Bug.mute() adds a BugMute record for the person passed to it.
        with person_logged_in(self.person):
            self.bug.mute(self.person, self.person)
            naked_bug = removeSecurityProxy(self.bug)
            bug_mute = naked_bug._getMutes(self.person).one()
            self.assertEqual(self.bug, bug_mute.bug)
            self.assertEqual(self.person, bug_mute.person)

    def test_mute_mutes_muter(self):
        # When exposed in the web API, the mute method regards the
        # first, `person` argument as optional, and the second
        # `muted_by` argument is supplied from the request.  In this
        # case, the person should be the muter.
        with person_logged_in(self.person):
            self.bug.mute(None, self.person)
            self.assertTrue(self.bug.isMuted(self.person))

    def test_mute_mutes_user_with_existing_subscription(self):
        # Bug.mute() will not touch the existing subscription.
        with person_logged_in(self.person):
            subscription = self.bug.subscribe(
                self.person, self.person,
                level=BugNotificationLevel.METADATA)
            self.bug.mute(self.person, self.person)
            self.assertTrue(self.bug.isMuted(self.person))
            self.assertEqual(
                BugNotificationLevel.METADATA,
                subscription.bug_notification_level)

    def test_unmute_unmutes_user(self):
        # Bug.unmute() will remove a muted subscription for the user
        # passed to it.
        with person_logged_in(self.person):
            self.bug.mute(self.person, self.person)
            self.assertTrue(self.bug.isMuted(self.person))
            self.bug.unmute(self.person, self.person)
            self.assertFalse(self.bug.isMuted(self.person))

    def test_unmute_returns_direct_subscription(self):
        # Bug.unmute() returns the previously muted direct subscription, if
        # any.
        with person_logged_in(self.person):
            self.bug.mute(self.person, self.person)
            self.assertEqual(True, self.bug.isMuted(self.person))
            self.assertEqual(None, self.bug.unmute(self.person, self.person))
            self.assertEqual(False, self.bug.isMuted(self.person))
            subscription = self.bug.subscribe(
                self.person, self.person,
                level=BugNotificationLevel.METADATA)
            self.bug.mute(self.person, self.person)
            self.assertEqual(True, self.bug.isMuted(self.person))
            self.assertEqual(
                subscription, self.bug.unmute(self.person, self.person))

    def test_unmute_mutes_unmuter(self):
        # When exposed in the web API, the unmute method regards the
        # first, `person` argument as optional, and the second
        # `unmuted_by` argument is supplied from the request.  In this
        # case, the person should be the muter.
        with person_logged_in(self.person):
            self.bug.mute(self.person, self.person)
            self.bug.unmute(None, self.person)
            self.assertFalse(self.bug.isMuted(self.person))


class TestBugSnapshotting(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugSnapshotting, self).setUp()
        self.bug = self.factory.makeBug()
        self.person = self.factory.makePerson()

    def test_bug_snapshot_does_not_include_messages(self):
        # A snapshot of a bug does not include its messages or
        # attachments (which get the messages from the database).  If it
        # does, the webservice can become unusable if changes are made
        # to bugs with many comments, such as bug 1. See, for instance,
        # bug 744888.  This test is primarily to keep the problem from
        # slipping in again.  To do so, we resort to somewhat
        # extraordinary measures.  In addition to verifying that the
        # snapshot does not have the attributes that currently trigger
        # the problem, we also actually look at the SQL that is
        # generated by creating the snapshot.  With this, we can verify
        # that the Message table is not included.  This is ugly, but
        # this has a chance of fighting against future eager loading
        # optimizations that might trigger the problem again.
        with person_logged_in(self.person):
            with StormStatementRecorder() as recorder:
                Snapshot(self.bug, providing=providedBy(self.bug))
            sql_statements = recorder.statements
        # This uses "self" as a marker to show that the attribute does not
        # exist.  We do not use hasattr because it eats exceptions.
        #self.assertTrue(getattr(snapshot, 'messages', self) is self)
        #self.assertTrue(getattr(snapshot, 'attachments', self) is self)
        for sql in sql_statements:
            # We are going to be aggressive about looking for the problem in
            # the SQL.  We'll split the SQL up by whitespace, and then look
            # for strings that start with "message".  If that is too
            # aggressive in the future from some reason, please do adjust the
            # test appropriately.
            sql_tokens = sql.lower().split()
            self.assertEqual(
                [token for token in sql_tokens
                 if token.startswith('message')],
                [])
            self.assertEqual(
                [token for token in sql_tokens
                 if token.startswith('bugactivity')],
                [])


class TestBugCreation(TestCaseWithFactory):
    """Tests for bug creation."""

    layer = DatabaseFunctionalLayer

    def test_CreateBugParams_accepts_importance(self):
        # The importance of the initial bug task can be set using
        # CreateBugParams
        owner = self.factory.makePerson()
        target = self.factory.makeProduct(owner=owner)
        with person_logged_in(owner):
            params = CreateBugParams(
                owner=owner, title="A bug", comment="Nothing important.",
                importance=BugTaskImportance.HIGH)
            params.setBugTarget(product=target)
            bug = getUtility(IBugSet).createBug(params)
            self.assertEqual(
                bug.default_bugtask.importance, params.importance)

    def test_CreateBugParams_accepts_assignee(self):
        # The assignee of the initial bug task can be set using
        # CreateBugParams
        owner = self.factory.makePerson()
        target = self.factory.makeProduct(owner=owner)
        with person_logged_in(owner):
            params = CreateBugParams(
                owner=owner, title="A bug", comment="Nothing important.",
                assignee=owner)
            params.setBugTarget(product=target)
            bug = getUtility(IBugSet).createBug(params)
            self.assertEqual(
                bug.default_bugtask.assignee, params.assignee)

    def test_CreateBugParams_accepts_milestone(self):
        # The milestone of the initial bug task can be set using
        # CreateBugParams
        owner = self.factory.makePerson()
        target = self.factory.makeProduct(owner=owner)
        with person_logged_in(owner):
            params = CreateBugParams(
                owner=owner, title="A bug", comment="Nothing important.",
                milestone=self.factory.makeMilestone(product=target))
            params.setBugTarget(product=target)
            bug = getUtility(IBugSet).createBug(params)
            self.assertEqual(
                bug.default_bugtask.milestone, params.milestone)

    def test_CreateBugParams_accepts_status(self):
        # The status of the initial bug task can be set using
        # CreateBugParams
        owner = self.factory.makePerson()
        target = self.factory.makeProduct(owner=owner)
        with person_logged_in(owner):
            params = CreateBugParams(
                owner=owner, title="A bug", comment="Nothing important.",
                status=BugTaskStatus.TRIAGED)
            params.setBugTarget(product=target)
            bug = getUtility(IBugSet).createBug(params)
            self.assertEqual(
                bug.default_bugtask.status, params.status)

    def test_CreateBugParams_rejects_not_allowed_importance_changes(self):
        # createBug() will reject any importance value passed by users
        # who don't have the right to set the importance.
        person = self.factory.makePerson()
        target = self.factory.makeProduct()
        with person_logged_in(person):
            params = CreateBugParams(
                owner=person, title="A bug", comment="Nothing important.",
                importance=BugTaskImportance.HIGH)
            params.setBugTarget(product=target)
            self.assertRaises(
                UserCannotEditBugTaskImportance,
                getUtility(IBugSet).createBug, params)

    def test_CreateBugParams_rejects_not_allowed_assignee_changes(self):
        # createBug() will reject any importance value passed by users
        # who don't have the right to set the assignee.
        person = self.factory.makePerson()
        person_2 = self.factory.makePerson()
        target = self.factory.makeProduct()
        # Setting the target's bug supervisor means that
        # canTransitionToAssignee() will return False for `person` if
        # another Person is passed as `assignee`.
        with person_logged_in(target.owner):
            target.setBugSupervisor(target.owner, target.owner)
        with person_logged_in(person):
            params = CreateBugParams(
                owner=person, title="A bug", comment="Nothing important.",
                assignee=person_2)
            params.setBugTarget(product=target)
            self.assertRaises(
                UserCannotEditBugTaskAssignee,
                getUtility(IBugSet).createBug, params)

    def test_CreateBugParams_rejects_not_allowed_milestone_changes(self):
        # createBug() will reject any importance value passed by users
        # who don't have the right to set the milestone.
        person = self.factory.makePerson()
        target = self.factory.makeProduct()
        with person_logged_in(person):
            params = CreateBugParams(
                owner=person, title="A bug", comment="Nothing important.",
                milestone=self.factory.makeMilestone(product=target))
            params.setBugTarget(product=target)
            self.assertRaises(
                UserCannotEditBugTaskMilestone,
                getUtility(IBugSet).createBug, params)

    def test_createBugWithoutTarget_cve(self):
        cve = self.factory.makeCVE('1999-1717')
        target = self.factory.makeProduct()
        person = self.factory.makePerson()
        with person_logged_in(person):
            params = CreateBugParams(
                owner=person, title="A bug", comment="bad thing.", cve=cve)
        params.setBugTarget(product=target)
        bug = getUtility(IBugSet).createBug(params)
        self.assertEqual([cve], [cve_link.cve for cve_link in bug.cve_links])


class TestBugAccessPolicy(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_setAccessPolicy(self):
        product = self.factory.makeProduct()
        policy = self.factory.makeAccessPolicy(pillar=product)
        bug = self.factory.makeBug(product=product)
        self.assertIs(None, bug.access_policy)
        with person_logged_in(bug.owner):
            bug.setAccessPolicy(policy)
        self.assertEqual(policy, bug.access_policy)

    def test_setAccessPolicy_other_pillar(self):
        policy = self.factory.makeAccessPolicy()
        bug = self.factory.makeBug()
        self.assertIs(None, bug.access_policy)
        with person_logged_in(bug.owner):
            self.assertRaises(
                UnsuitableAccessPolicyError, bug.setAccessPolicy, policy)
        self.assertIs(None, bug.access_policy)
