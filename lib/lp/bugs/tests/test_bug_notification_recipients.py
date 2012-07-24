# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests related to bug notification recipients."""

__metaclass__ = type

from lp.registry.enums import InformationType
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestBugNotificationRecipients(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_public_bug(self):
        bug = self.factory.makeBug()
        self.assertContentEqual(
            [bug.owner], bug.getBugNotificationRecipients())

    def test_public_bug_with_subscriber(self):
        bug = self.factory.makeBug()
        subscriber = self.factory.makePerson()
        with person_logged_in(bug.owner):
            bug.subscribe(subscriber, bug.owner)
        self.assertContentEqual(
            [bug.owner, subscriber], bug.getBugNotificationRecipients())

    def test_public_bug_with_structural_subscriber(self):
        subscriber = self.factory.makePerson()
        product = self.factory.makeProduct()
        with person_logged_in(subscriber):
            product.addBugSubscription(subscriber, subscriber)
        bug = self.factory.makeBug(product=product)
        self.assertContentEqual(
            [bug.owner, subscriber], bug.getBugNotificationRecipients())

    def test_public_bug_assignee(self):
        assignee = self.factory.makePerson()
        bug = self.factory.makeBug()
        with person_logged_in(bug.owner):
            bug.default_bugtask.transitionToAssignee(assignee)
        self.assertContentEqual(
            [bug.owner, assignee], bug.getBugNotificationRecipients())

    def test_public_bug_with_duplicate_subscriber(self):
        subscriber = self.factory.makePerson()
        bug = self.factory.makeBug()
        dupe = self.factory.makeBug()
        with person_logged_in(dupe.owner):
            dupe.subscribe(subscriber, dupe.owner)
            dupe.markAsDuplicate(bug)
        self.assertContentEqual(
            [bug.owner, dupe.owner, subscriber],
            bug.getBugNotificationRecipients())

    def test_public_bug_linked_to_question(self):
        question = self.factory.makeQuestion()
        bug = self.factory.makeBug()
        with person_logged_in(question.owner):
            question.linkBug(bug)
        self.assertContentEqual(
            [bug.owner, question.owner], bug.getBugNotificationRecipients())

    def test_private_bug(self):
        owner = self.factory.makePerson()
        bug = self.factory.makeBug(
            owner=owner, information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            self.assertContentEqual(
                [owner], bug.getBugNotificationRecipients())

    def test_private_bug_with_subscriber(self):
        owner = self.factory.makePerson()
        subscriber = self.factory.makePerson()
        bug = self.factory.makeBug(
            owner=owner, information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            bug.subscribe(subscriber, owner)
            self.assertContentEqual(
                [owner, subscriber], bug.getBugNotificationRecipients())

    def test_private_bug_with_structural_subscriber(self):
        owner = self.factory.makePerson()
        subscriber = self.factory.makePerson()
        product = self.factory.makeProduct()
        with person_logged_in(subscriber):
            product.addBugSubscription(subscriber, subscriber)
        bug = self.factory.makeBug(
            product=product, owner=owner,
            information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            self.assertContentEqual(
                [owner], bug.getBugNotificationRecipients())

    def test_private_bug_assignee(self):
        owner = self.factory.makePerson()
        assignee = self.factory.makePerson()
        bug = self.factory.makeBug(
            owner=owner, information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            bug.default_bugtask.transitionToAssignee(assignee)
            self.assertContentEqual(
                [owner], bug.getBugNotificationRecipients())

    def test_private_bug_with_duplicate_subscriber(self):
        owner = self.factory.makePerson()
        subscriber = self.factory.makePerson()
        bug = self.factory.makeBug(
            owner=owner, information_type=InformationType.USERDATA)
        dupe = self.factory.makeBug(owner=owner)
        with person_logged_in(owner):
            dupe.subscribe(subscriber, owner)
            dupe.markAsDuplicate(bug)
            self.assertContentEqual(
                [owner], bug.getBugNotificationRecipients())

    def test_private_bug_linked_to_question(self):
        owner = self.factory.makePerson()
        question = self.factory.makeQuestion(owner=owner)
        bug = self.factory.makeBug(
            owner=owner, information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            question.linkBug(bug)
            self.assertContentEqual(
                [owner], bug.getBugNotificationRecipients())
