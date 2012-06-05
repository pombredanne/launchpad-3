# Copyright 2011-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for visibility of a bug."""

from lp.registry.enums import InformationType
from lp.services.features.testing import FeatureFixture
from lp.testing import (
    celebrity_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.fixture import DisableTriggerFixture
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    ZopelessDatabaseLayer,
    )


LEGACY_VISIBILITY_FLAG = {
    u"disclosure.legacy_subscription_visibility.enabled": u"true"}
TRIGGERS_REMOVED_FLAG = {
    u"disclosure.access_mirror_triggers.removed": u"true"}


class TestPublicBugVisibility(TestCaseWithFactory):
    """Test visibility for a public bug."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPublicBugVisibility, self).setUp()
        owner = self.factory.makePerson(name="bugowner")
        self.bug = self.factory.makeBug(owner=owner)

    def test_publicBugAnonUser(self):
        # Since the bug is public, the anonymous user can see it.
        self.assertTrue(self.bug.userCanView(None))

    def test_publicBugRegularUser(self):
        # A regular (non-privileged) user can view a public bug.
        user = self.factory.makePerson()
        self.assertTrue(self.bug.userCanView(user))


class TestPrivateBugVisibility(TestCaseWithFactory):
    """Test visibility for a private bug."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestPrivateBugVisibility, self).setUp()
        self.owner = self.factory.makePerson(name="bugowner")
        self.product_owner = self.factory.makePerson(name="productowner")
        self.product = self.factory.makeProduct(
            name="regular-product", owner=self.product_owner)
        self.bug_team = self.factory.makeTeam(
            name="bugteam", owner=self.product.owner)
        self.bug_team_member = self.factory.makePerson(name="bugteammember")
        with celebrity_logged_in('admin'):
            self.bug_team.addMember(self.bug_team_member, self.product.owner)
            self.product.setBugSupervisor(
                bug_supervisor=self.bug_team,
                user=self.product.owner)
        self.bug = self.factory.makeBug(
            owner=self.owner, product=self.product,
            information_type=InformationType.USERDATA)

    def test_privateBugRegularUser(self):
        # A regular (non-privileged) user can not view a private bug.
        user = self.factory.makePerson()
        self.assertFalse(self.bug.userCanView(user))

    def test_privateBugOwner(self):
        # The bug submitter may view a private bug.
        self.assertTrue(self.bug.userCanView(self.owner))

    def test_privateBugSupervisor(self):
        # A member of the bug supervisor team can not see a private bug.
        self.assertFalse(self.bug.userCanView(self.bug_team_member))

    def test_privateBugSubscriber(self):
        # A person subscribed to a private bug can see it.
        user = self.factory.makePerson()
        with celebrity_logged_in('admin'):
            self.bug.subscribe(user, self.owner)
        self.assertTrue(self.bug.userCanView(user))

    def test_privateBugAnonUser(self):
        # Since the bug is private, the anonymous user cannot see it.
        self.assertFalse(self.bug.userCanView(None))

    @property
    def disable_trigger_fixture(self):
        # XXX 2012-05-22 wallyworld bug=1002596
        # No need to use this fixture when triggers are removed.
        return DisableTriggerFixture(
                {'bugsubscription':
                     'bugsubscription_mirror_legacy_access_t',
                 'bug': 'bug_mirror_legacy_access_t',
                 'bugtask': 'bugtask_mirror_legacy_access_t',
            })

    def test_privateBugUnsubscribeRevokesVisibility(self):
        # A person unsubscribed from a private bug can no longer see it.
        # Requires feature flag since the default model behaviour is to leave
        # any access grants untouched.
        # This test disables the current temporary database triggers which
        # mirror subscription status into visibility.
        with FeatureFixture(LEGACY_VISIBILITY_FLAG):
            user = self.factory.makePerson()
            with celebrity_logged_in('admin'):
                self.bug.subscribe(user, self.owner)
                self.assertTrue(self.bug.userCanView(user))
                with self.disable_trigger_fixture:
                    self.bug.unsubscribe(user, self.owner)
            self.assertFalse(self.bug.userCanView(user))

    def test_privateBugUnsubscribeRetainsVisibility(self):
        # A person unsubscribed from a private bug can still see it if the
        # feature flag to enable legacy subscription visibility is not set.
        # This test disables the current temporary database triggers which
        # mirror subscription status into visibility.
        user = self.factory.makePerson()
        with celebrity_logged_in('admin'):
            self.bug.subscribe(user, self.owner)
            self.assertTrue(self.bug.userCanView(user))
            with self.disable_trigger_fixture:
                self.bug.unsubscribe(user, self.owner)
        self.assertTrue(self.bug.userCanView(user))

    def test_subscribeGrantsVisibilityWithTriggersRemoved(self):
        # When a user is subscribed to a bug, they are granted access. In this
        # test, the database triggers are removed and so model code is used.
        with FeatureFixture(TRIGGERS_REMOVED_FLAG):
            with self.disable_trigger_fixture:
                user = self.factory.makePerson()
                self.assertFalse(self.bug.userCanView(user))
                with celebrity_logged_in('admin'):
                    self.bug.subscribe(user, self.owner)
                    self.assertTrue(self.bug.userCanView(user))

    def test_subscribeGrantsVisibilityUsingTriggers(self):
        # When a user is subscribed to a bug, they are granted access. In this
        # test, the database triggers are used.
        user = self.factory.makePerson()
        self.assertFalse(self.bug.userCanView(user))
        with celebrity_logged_in('admin'):
            self.bug.subscribe(user, self.owner)
            self.assertTrue(self.bug.userCanView(user))
