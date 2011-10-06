# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.errors import UserCannotUnsubscribePerson
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class TestSpecificationSubscription(TestCaseWithFactory):
    """ Test whether a user can unsubscribe someone

    As user can't unsubscribe just anyone from a spec. To check whether
    someone can be unusubscribed, the canBeUnsubscribedByUser() method on
    the SpecificationSubscription object is used.
    """

    layer = DatabaseFunctionalLayer

    def _make_subscription(self):
        spec = self.factory.makeSpecification()
        subscriber = self.factory.makePerson()
        subscribed_by = self.factory.makePerson()
        subscription = spec.subscribe(subscriber, subscribed_by)
        return spec, subscriber, subscribed_by, subscription

    def test_can_unsubscribe_self(self):
        # The user can of course unsubscribe himself, even if someone else
        # subscribed him.
        (spec, subscriber,
            subscribed_by, subscription) = self._make_subscription()
        self.assertTrue(subscription.canBeUnsubscribedByUser(subscriber))

    def test_subscriber_cannot_unsubscribe_user(self):
        # The one who subscribed the subscriber doesn't have permission to
        # unsubscribe him.
        (spec, subscriber,
            subscribed_by, subscription) = self._make_subscription()
        self.assertFalse(subscription.canBeUnsubscribedByUser(subscribed_by))

    def test_anonymous_cannot_unsubscribe(self):
        # The anonymous user (represented by None) can't unsubscribe anyone.
        (spec, subscriber,
            subscribed_by, subscription) = self._make_subscription()
        self.assertFalse(subscription.canBeUnsubscribedByUser(None))

    def test_can_unsubscribe_team(self):
        # A user can unsubscribe a team he's a member of.
        (spec, subscriber,
            subscribed_by, subscription) = self._make_subscription()
        team = self.factory.makeTeam()
        member = self.factory.makePerson()
        with person_logged_in(member):
            member.join(team)
            subscription = spec.subscribe(team, subscribed_by)
        self.assertTrue(subscription.canBeUnsubscribedByUser(member))

        non_member = self.factory.makePerson()
        self.assertFalse(subscription.canBeUnsubscribedByUser(non_member))

    def test_cannot_unsubscribe_team(self):
        # A user cannot unsubscribe a team he's a not member of.
        (spec, subscriber,
            subscribed_by, subscription) = self._make_subscription()
        team = self.factory.makeTeam()
        member = self.factory.makePerson()
        with person_logged_in(member):
            member.join(team)
            subscription = spec.subscribe(team, subscribed_by)
        non_member = self.factory.makePerson()
        self.assertFalse(subscription.canBeUnsubscribedByUser(non_member))

    def test_unallowed_unsubscribe_raises(self):
        # A spec's unsubscribe method uses canBeUnsubscribedByUser to check
        # that the unsubscribing user has the appropriate permissions.
        # unsubscribe will raise an exception if the user does not have
        # permission.
        (spec, subscriber,
            subscribed_by, subscription) = self._make_subscription()
        person = self.factory.makePerson()
        self.assertRaises(
            UserCannotUnsubscribePerson, spec.unsubscribe, subscriber, person)
