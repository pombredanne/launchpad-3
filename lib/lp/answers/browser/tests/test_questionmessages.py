# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the various rules around question comment visibility."""

__metaclass__ = type

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.testing.pages import find_tag_by_id
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.coop.answersbugs.visibility import TestMessageVisibilityMixin
from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    )


class TestQuestionMessageVisibility(
        BrowserTestCase, TestMessageVisibilityMixin):

    layer = DatabaseFunctionalLayer

    def makeHiddenMessage(self):
        administrator = getUtility(ILaunchpadCelebrities).admin.teamowner
        with person_logged_in(administrator):
            question = self.factory.makeQuestion()
            comment = question.addComment(administrator, self.comment_text)
            removeSecurityProxy(comment).message.visible = False
        return question

    def getView(self, context, user=None, no_login=False):
        view = self.getViewBrowser(
            context=context,
            user=user,
            no_login=no_login)
        return view


class TestQuestionSpamControls(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def makeQuestionWithMessage(self):
        administrator = getUtility(ILaunchpadCelebrities).admin.teamowner
        question = self.factory.makeQuestion()
        body = self.factory.getUniqueString()
        with person_logged_in(administrator):
            question.addComment(administrator, body)
        return question

    def test_admin_sees_spam_control(self):
        question = self.makeQuestionWithMessage()
        administrator = self.factory.makeAdministrator()
        view = self.getViewBrowser(context=question, user=administrator)
        spam_link = find_tag_by_id(view.contents, 'mark-spam-1')
        self.assertIsNot(None, spam_link)

    def test_registry_sees_spam_control(self):
        question = self.makeQuestionWithMessage()
        registry_expert = self.factory.makeRegistryExpert()
        view = self.getViewBrowser(context=question, user=registry_expert)
        spam_link = find_tag_by_id(view.contents, 'mark-spam-1')
        self.assertIsNot(None, spam_link)

    def test_anon_doesnt_see_spam_control(self):
        question = self.makeQuestionWithMessage()
        view = self.getViewBrowser(context=question, no_login=True)
        spam_link = find_tag_by_id(view.contents, 'mark-spam-1')
        self.assertIs(None, spam_link)

    def test_random_doesnt_see_spam_control(self):
        question = self.makeQuestionWithMessage()
        view = self.getViewBrowser(context=question)
        spam_link = find_tag_by_id(view.contents, 'mark-spam-1')
        self.assertIs(None, spam_link)
