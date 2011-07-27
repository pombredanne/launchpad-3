# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class TestQuestionDirectSubscribers(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_get_direct_subscribers(self):
        question = self.factory.makeQuestion()
        subscriber = self.factory.makePerson()
        subscribers = [question.owner, subscriber]
        with person_logged_in(subscriber):
            question.subscribe(subscriber, subscriber)

        direct_subscribers = question.getDirectSubscribers()
        self.assertEqual(
            set(subscribers), set(direct_subscribers),
            "Subscribers did not match expected value.")

    def test_get_direct_subscribers_with_details_other_subscriber(self):
        # getDirectSubscribersWithDetails() returns
        # Person and QuestionSubscription records in one go.
        question = self.factory.makeQuestion()
        with person_logged_in(question.owner):
            # Unsubscribe question owner so it doesn't taint the result.
            question.unsubscribe(question.owner, question.owner)
        subscriber = self.factory.makePerson()
        subscribee = self.factory.makePerson()
        with person_logged_in(subscriber):
            subscription = question.subscribe(subscribee, subscriber)
        self.assertContentEqual(
            [(subscribee, subscription)],
            question.getDirectSubscribersWithDetails())

    def test_get_direct_subscribers_with_details_self_subscribed(self):
        # getDirectSubscribersWithDetails() returns
        # Person and QuestionSubscription records in one go.
        question = self.factory.makeQuestion()
        with person_logged_in(question.owner):
            # Unsubscribe question owner so it doesn't taint the result.
            question.unsubscribe(question.owner, question.owner)
        subscriber = self.factory.makePerson()
        with person_logged_in(subscriber):
            subscription = question.subscribe(subscriber, subscriber)
        self.assertContentEqual(
            [(subscriber, subscription)],
            question.getDirectSubscribersWithDetails())
