# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the various rules around question comment visibility."""

__metaclass__ = type

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.coop.answersbugs.visibility import (
    TestHideMessageControlMixin,
    TestMessageVisibilityMixin,
    )
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


class TestHideQuestionMessageControls(
        BrowserTestCase, TestHideMessageControlMixin):

    layer = DatabaseFunctionalLayer

    def getContext(self):
        administrator = getUtility(ILaunchpadCelebrities).admin.teamowner
        question = self.factory.makeQuestion()
        body = self.factory.getUniqueString()
        with person_logged_in(administrator):
            question.addComment(administrator, body)
        return question

    def getView(self, context, user=None, no_login=False):
        view = self.getViewBrowser(
            context=context,
            user=user,
            no_login=no_login)
        return view
