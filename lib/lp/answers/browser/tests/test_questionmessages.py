# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the various rules around question comment visibility."""

__metaclass__ = type

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.testing.pages import find_tag_by_id
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    )


class TestQuestionCommentVisibility(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def makeQuestionWithHiddenComment(self, questionbody=None):
        administrator = getUtility(ILaunchpadCelebrities).admin.teamowner
        with person_logged_in(administrator):
            question = self.factory.makeQuestion()
            comment = question.addComment(administrator, questionbody)
            removeSecurityProxy(comment).message.visible = False
        return question

    def test_admin_can_see_comments(self):
        comment_text = "You can't see me."
        question = self.makeQuestionWithHiddenComment(comment_text)
        administrator = self.factory.makeAdministrator()
        view = self.getViewBrowser( context=question, user=administrator)
        self.assertTrue(
           comment_text in view.contents,
           "Administrator cannot see the hidden comment.")

    def test_registry_can_see_comments(self):
        comment_text = "You can't see me."
        question = self.makeQuestionWithHiddenComment(comment_text)
        registry_expert = self.factory.makeRegistryExpert()
        view = self.getViewBrowser(context=question, user=registry_expert)
        self.assertTrue(
           comment_text in view.contents,
           "Registy member cannot see the hidden comment.")

    def test_anon_cannot_see_comments(self):
        comment_text = "You can't see me."
        question = self.makeQuestionWithHiddenComment(comment_text)
        view = self.getViewBrowser(context=question, no_login=True)
        self.assertFalse(
           comment_text in view.contents,
           "Anonymous person can see the hidden comment.")

    def test_random_cannot_see_comments(self):
        comment_text = "You can't see me."
        question = self.makeQuestionWithHiddenComment(comment_text)
        view = self.getViewBrowser(context=question)
        self.assertFalse(
           comment_text in view.contents,
           "Random user can see the hidden comment.")


class TestQuestionSpamControls(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def makeQuestionWithMessage(self):
        administrator = getUtility(ILaunchpadCelebrities).admin.teamowner
        question = self.factory.makeQuestion()
        body = self.factory.getUniqueString()
        with person_logged_in(administrator): 
            comment = question.addComment(administrator, body)
        return question

    def test_admin_sees_spam_control(self):
        question = self.makeQuestionWithMessage()
        administrator = self.factory.makeAdministrator()
        view = self.getViewBrowser(context=question, user=administrator)
        spam_link = find_tag_by_id(view.contents, 'mark-spam')
        self.assertIsNot(None, spam_link)

    def test_registry_sees_spam_control(self):
        question = self.makeQuestionWithMessage()
        registry_expert = self.factory.makeRegistryExpert()
        view = self.getViewBrowser(context=question, user=registry_expert)
        spam_link = find_tag_by_id(view.contents, 'mark-spam')
        self.assertIsNot(None, spam_link)

    def test_anon_doesnt_see_spam_control(self):
        question = self.makeQuestionWithMessage()
        view = self.getViewBrowser(context=question, no_login=True)
        spam_link = find_tag_by_id(view.contents, 'mark-spam')
        self.assertIs(None, spam_link)

    def test_random_doesnt_see_spam_control(self):
        question = self.makeQuestionWithMessage()
        view = self.getViewBrowser(context=question)
        spam_link = find_tag_by_id(view.contents, 'mark-spam')
        self.assertIs(None, spam_link)

