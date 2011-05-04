# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the various rules around question comment visibility."""

__metaclass__ = type

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    )


class TestQuestionCommentVisibility(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def _makeQuestionWithHiddenComment(self, questionbody=None):
        administrator = getUtility(ILaunchpadCelebrities).admin.teamowner
        with person_logged_in(administrator):
            question = self.factory.makeQuestion()
            comment = question.addComment(administrator, questionbody)
            removeSecurityProxy(comment).message.visible = False
        return question

    def _getUserForTest(self, team=None):
        person = self.factory.makePerson()
        if team is not None:
            with person_logged_in(team.teamowner):
                team.addMember(person, team.teamowner)
        return person

    def test_admin_can_see_comments(self):
        comment_text = "You can't see me."
        question = self._makeQuestionWithHiddenComment(comment_text)
        admin_team = getUtility(ILaunchpadCelebrities).admin
        administrator = self._getUserForTest(admin_team)
        view = self.getViewBrowser(
            context=question, user=administrator)
        self.assertTrue(
           comment_text in view.contents,
           "Administrator cannot see the hidden comment.")

    def test_registry_can_see_comments(self):
        comment_text = "You can't see me."
        question = self._makeQuestionWithHiddenComment(comment_text)
        registry_team = getUtility(ILaunchpadCelebrities).registry_experts
        registry_expert = self._getUserForTest(registry_team)
        view = self.getViewBrowser(
            context=question, user=registry_expert)
        self.assertTrue(
           comment_text in view.contents,
           "Registy member cannot see the hidden comment.")

    def test_anon_cannot_see_comments(self):
        comment_text = "You can't see me."
        question = self._makeQuestionWithHiddenComment(comment_text)
        view = self.getViewBrowser(context=question, no_login=True)
        self.assertFalse(
           comment_text in view.contents,
           "Anonymous person can see the hidden comment.")

    def test_random_cannot_see_comments(self):
        comment_text = "You can't see me."
        question = self._makeQuestionWithHiddenComment(comment_text)
        view = self.getViewBrowser(context=question)
        self.assertFalse(
           comment_text in view.contents,
           "Random user can see the hidden comment.")
