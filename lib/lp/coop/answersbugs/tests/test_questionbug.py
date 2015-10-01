# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from lp.services.features.testing import FeatureFixture
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestQuestionBugLinks(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_link_and_unlink(self):
        login_person(self.factory.makePerson())

        bug1 = self.factory.makeBug()
        bug2 = self.factory.makeBug()
        question1 = self.factory.makeQuestion()
        question2 = self.factory.makeQuestion()
        self.assertContentEqual([], bug1.questions)
        self.assertContentEqual([], bug2.questions)
        self.assertContentEqual([], question1.bugs)
        self.assertContentEqual([], question2.bugs)

        question1.linkBug(bug1)
        question2.linkBug(bug1)
        question1.linkBug(bug2)
        self.assertContentEqual([bug1, bug2], question1.bugs)
        self.assertContentEqual([bug1], question2.bugs)
        self.assertContentEqual([question1, question2], bug1.questions)
        self.assertContentEqual([question1], bug2.questions)

        question1.unlinkBug(bug1)
        self.assertContentEqual([bug2], question1.bugs)
        self.assertContentEqual([bug1], question2.bugs)
        self.assertContentEqual([question2], bug1.questions)
        self.assertContentEqual([question1], bug2.questions)

        question1.unlinkBug(bug2)
        self.assertContentEqual([], question1.bugs)
        self.assertContentEqual([bug1], question2.bugs)
        self.assertContentEqual([question2], bug1.questions)
        self.assertContentEqual([], bug2.questions)

    def test_link_subscribes_creator_to_bug(self):
        login_person(self.factory.makePerson())
        bug = self.factory.makeBug()
        question = self.factory.makeQuestion()
        self.assertFalse(bug.isSubscribed(question.owner))

        # Linking a bug to a question subscribes the question's creator
        # to the bug.
        question.linkBug(bug)
        self.assertTrue(bug.isSubscribed(question.owner))

        # If the creator manually unsubscribes, recreating the existing
        # link does nothing.
        bug.unsubscribe(question.owner, question.owner)
        self.assertFalse(bug.isSubscribed(question.owner))
        question.linkBug(bug)
        self.assertFalse(bug.isSubscribed(question.owner))

    def test_link_copes_with_existing_subscription(self):
        # Linking a bug to a question doesn't complain if the creator is
        # already subscriber.
        login_person(self.factory.makePerson())
        bug = self.factory.makeBug()
        question = self.factory.makeQuestion()
        bug.subscribe(question.owner, question.owner)
        self.assertTrue(bug.isSubscribed(question.owner))
        question.linkBug(bug)
        self.assertTrue(bug.isSubscribed(question.owner))

    def test_unlink_unsubscribes_creator_from_bug(self):
        login_person(self.factory.makePerson())
        bug = self.factory.makeBug()
        question = self.factory.makeQuestion()
        question.linkBug(bug)
        self.assertTrue(bug.isSubscribed(question.owner))

        # Unlinking the bug unsubscribes the question's creator.
        question.unlinkBug(bug)
        self.assertFalse(bug.isSubscribed(question.owner))

        # Reunlinking an unlinked bug doesn't unsubscribe.
        bug.subscribe(question.owner, question.owner)
        question.unlinkBug(bug)
        self.assertTrue(bug.isSubscribed(question.owner))

    def test_unlink_copes_with_no_subscription(self):
        # Unlinking a bug from a question doesn't complain if the
        # creator isn't subscribed.
        login_person(self.factory.makePerson())
        bug = self.factory.makeBug()
        question = self.factory.makeQuestion()
        question.linkBug(bug)
        bug.unsubscribe(question.owner, question.owner)
        self.assertFalse(bug.isSubscribed(question.owner))
        question.unlinkBug(bug)
        self.assertFalse(bug.isSubscribed(question.owner))


class TestQuestionBugLinksWithXRef(TestQuestionBugLinks):

    def setUp(self):
        super(TestQuestionBugLinksWithXRef, self).setUp()
        self.useFixture(FeatureFixture({'bugs.xref_buglinks.query': 'true'}))


class TestQuestionBugLinksWithXRefAndNoOld(TestQuestionBugLinks):

    def setUp(self):
        super(TestQuestionBugLinksWithXRefAndNoOld, self).setUp()
        self.useFixture(FeatureFixture({
            'bugs.xref_buglinks.query': 'true',
            'bugs.xref_buglinks.write_old.disabled': 'true'}))
