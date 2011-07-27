# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webservice unit tests related to Launchpad questions."""

__metaclass__ = type

import transaction

from canonical.testing import (
    AppServerLayer,
    )
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    ws_object,
    )


class TestQuestionWebServiceSubscription(TestCaseWithFactory):

    layer = AppServerLayer

    def test_subscribe(self):
        # Test subscribe() API.
        person = self.factory.makePerson()
        with person_logged_in(person):
            db_question = self.factory.makeQuestion()
            db_person = self.factory.makePerson()
            launchpad = self.factory.makeLaunchpadService()

        question = ws_object(launchpad, db_question)
        person = ws_object(launchpad, db_person)
        question.subscribe(person=person)
        transaction.commit()

        # Check the results.
        self.assertTrue(db_question.isSubscribed(db_person))

    def test_unsubscribe(self):
        # Test unsubscribe() API.
        person = self.factory.makePerson()
        with person_logged_in(person):
            db_question = self.factory.makeQuestion()
            db_person = self.factory.makePerson()
            db_question.subscribe(person=db_person)
            launchpad = self.factory.makeLaunchpadService(person=db_person)

        question = ws_object(launchpad, db_question)
        person = ws_object(launchpad, db_person)
        question.unsubscribe(person=person)
        transaction.commit()

        # Check the results.
        self.assertFalse(db_question.isSubscribed(db_person))
