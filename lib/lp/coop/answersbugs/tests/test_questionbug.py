# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

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
