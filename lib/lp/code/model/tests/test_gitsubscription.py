# Copyright 2010-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the GitSubscription model object."""

__metaclass__ = type


from lp.app.enums import InformationType
from lp.app.errors import (
    SubscriptionPrivacyViolation,
    UserCannotUnsubscribePerson,
    )
from lp.code.enums import (
    BranchSubscriptionNotificationLevel,
    CodeReviewNotificationLevel,
    )
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestGitSubscriptions(TestCaseWithFactory):
    """Tests relating to Git repository subscriptions in general."""

    layer = DatabaseFunctionalLayer

    def test_owner_subscribed(self):
        # The owner of a repository is subscribed to the repository.
        repository = self.factory.makeGitRepository()
        [subscription] = list(repository.subscriptions)
        self.assertEqual(repository.owner, subscription.person)

    def test_subscribed_by_set(self):
        # The user subscribing is recorded along with the subscriber.
        subscriber = self.factory.makePerson()
        subscribed_by = self.factory.makePerson()
        repository = self.factory.makeGitRepository()
        subscription = repository.subscribe(
            subscriber, BranchSubscriptionNotificationLevel.NOEMAIL, None,
            CodeReviewNotificationLevel.NOEMAIL, subscribed_by)
        self.assertEqual(subscriber, subscription.person)
        self.assertEqual(subscribed_by, subscription.subscribed_by)

    def test_unsubscribe(self):
        # Test unsubscribing by the subscriber.
        subscription = self.factory.makeGitSubscription()
        subscriber = subscription.person
        repository = subscription.repository
        repository.unsubscribe(subscriber, subscriber)
        self.assertFalse(repository.hasSubscription(subscriber))

    def test_unsubscribe_by_subscriber(self):
        # Test unsubscribing by the person who subscribed the user.
        subscribed_by = self.factory.makePerson()
        subscription = self.factory.makeGitSubscription(
            subscribed_by=subscribed_by)
        subscriber = subscription.person
        repository = subscription.repository
        repository.unsubscribe(subscriber, subscribed_by)
        self.assertFalse(repository.hasSubscription(subscriber))

    def test_unsubscribe_by_unauthorized(self):
        # Test unsubscribing someone you shouldn't be able to.
        subscription = self.factory.makeGitSubscription()
        repository = subscription.repository
        self.assertRaises(
            UserCannotUnsubscribePerson,
            repository.unsubscribe,
            subscription.person,
            self.factory.makePerson())

    def test_cannot_subscribe_open_team_to_private_repository(self):
        # It is forbidden to subscribe a open team to a private repository.
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            information_type=InformationType.USERDATA, owner=owner)
        team = self.factory.makeTeam()
        with person_logged_in(owner):
            self.assertRaises(
                SubscriptionPrivacyViolation, repository.subscribe, team, None,
                None, None, owner)

    def test_subscribe_gives_access(self):
        # Subscribing a user to a repository gives them access.
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            information_type=InformationType.USERDATA, owner=owner)
        subscribee = self.factory.makePerson()
        with person_logged_in(owner):
            self.assertFalse(repository.visibleByUser(subscribee))
            repository.subscribe(
                subscribee, BranchSubscriptionNotificationLevel.NOEMAIL,
                None, CodeReviewNotificationLevel.NOEMAIL, owner)
            self.assertTrue(repository.visibleByUser(subscribee))

    def test_unsubscribe_removes_access(self):
        # Unsubscribing a user from a repository removes their access.
        owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(
            information_type=InformationType.USERDATA, owner=owner)
        subscribee = self.factory.makePerson()
        with person_logged_in(owner):
            repository.subscribe(
                subscribee, BranchSubscriptionNotificationLevel.NOEMAIL,
                None, CodeReviewNotificationLevel.NOEMAIL, owner)
            self.assertTrue(repository.visibleByUser(subscribee))
            repository.unsubscribe(subscribee, owner)
            self.assertFalse(repository.visibleByUser(subscribee))


class TestGitSubscriptionCanBeUnsubscribedbyUser(TestCaseWithFactory):
    """Tests for GitSubscription.canBeUnsubscribedByUser."""

    layer = DatabaseFunctionalLayer

    def test_none(self):
        # None for a user always returns False.
        subscription = self.factory.makeGitSubscription()
        self.assertFalse(subscription.canBeUnsubscribedByUser(None))

    def test_self_subscriber(self):
        # The subscriber has permission to unsubscribe.
        subscription = self.factory.makeGitSubscription()
        self.assertTrue(
            subscription.canBeUnsubscribedByUser(subscription.person))

    def test_non_subscriber_fails(self):
        # An unrelated person can't unsubscribe a user.
        subscription = self.factory.makeGitSubscription()
        editor = self.factory.makePerson()
        self.assertFalse(subscription.canBeUnsubscribedByUser(editor))

    def test_subscribed_by(self):
        # If a user subscribes someone else, the user can unsubscribe.
        subscribed_by = self.factory.makePerson()
        subscriber = self.factory.makePerson()
        subscription = self.factory.makeGitSubscription(
            person=subscriber, subscribed_by=subscribed_by)
        self.assertTrue(subscription.canBeUnsubscribedByUser(subscribed_by))

    def test_team_member_can_unsubscribe(self):
        # Any team member can unsubscribe the team from a repository.
        team = self.factory.makeTeam()
        member = self.factory.makePerson()
        with person_logged_in(team.teamowner):
            team.addMember(member, team.teamowner)
        subscription = self.factory.makeGitSubscription(
            person=team, subscribed_by=team.teamowner)
        self.assertTrue(subscription.canBeUnsubscribedByUser(member))

    def test_team_subscriber_can_unsubscribe(self):
        # A team can be unsubscribed by the subscriber even if they are not
        # a member.
        team = self.factory.makeTeam()
        subscribed_by = self.factory.makePerson()
        subscription = self.factory.makeGitSubscription(
            person=team, subscribed_by=subscribed_by)
        self.assertTrue(subscription.canBeUnsubscribedByUser(subscribed_by))

    def test_repository_person_owner_can_unsubscribe(self):
        # The repository owner can unsubscribe someone from the repository.
        repository_owner = self.factory.makePerson()
        repository = self.factory.makeGitRepository(owner=repository_owner)
        subscribed_by = self.factory.makePerson()
        subscriber = self.factory.makePerson()
        subscription = self.factory.makeGitSubscription(
            repository=repository, person=subscriber,
            subscribed_by=subscribed_by)
        self.assertTrue(subscription.canBeUnsubscribedByUser(repository_owner))

    def test_repository_team_owner_can_unsubscribe(self):
        # The repository team owner can unsubscribe someone from the
        # repository.
        #
        # If the owner of a repository is a team, then the team members can
        # unsubscribe someone.
        team_owner = self.factory.makePerson()
        team_member = self.factory.makePerson()
        repository_owner = self.factory.makeTeam(
            owner=team_owner, members=[team_member])
        repository = self.factory.makeGitRepository(owner=repository_owner)
        subscribed_by = self.factory.makePerson()
        subscriber = self.factory.makePerson()
        subscription = self.factory.makeGitSubscription(
            repository=repository, person=subscriber,
            subscribed_by=subscribed_by)
        self.assertTrue(subscription.canBeUnsubscribedByUser(team_owner))
        self.assertTrue(subscription.canBeUnsubscribedByUser(team_member))
