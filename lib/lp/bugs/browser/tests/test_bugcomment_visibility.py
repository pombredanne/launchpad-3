# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the various rules around bug comment visibility."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    BrowserTestCase,
    person_logged_in,
    )
from lp.testing.views import create_view, create_initialized_view


class TestBugCommentVisibility(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def _makeBugWithHiddenComment(self, bugbody=None):
        administrator = getUtility(ILaunchpadCelebrities).admin.teamowner
        bug = self.factory.makeBug()
        with person_logged_in(administrator):
            comment = self.factory.makeBugComment(bug=bug, body=bugbody)
            comment.visible = False
        return bug

    def _getUserForTest(self, team=None):
        person = self.factory.makePerson()
        if team is not None:
            with person_logged_in(team.teamowner):
                team.addMember(person, team.teamowner)
        return person

    def test_admin_can_see_comments(self):
        comment_text = "You can't see me."
        bug = self._makeBugWithHiddenComment(comment_text)
        admin_team = getUtility(ILaunchpadCelebrities).admin
        administrator = self._getUserForTest(admin_team)
        view = self.getViewBrowser(
            context=bug.default_bugtask, user=administrator)
        self.assertTrue(
           comment_text in view.contents,
           "Administrator cannot see the hidden comment.")
        
    def test_registry_can_see_comments(self):
        comment_text = "You can't see me."
        bug = self._makeBugWithHiddenComment(comment_text)
        registry_team = getUtility(ILaunchpadCelebrities).registry_experts
        registry_expert = self._getUserForTest(registry_team)
        view = self.getViewBrowser(
            context=bug.default_bugtask, user=registry_expert)
        self.assertTrue(
           comment_text in view.contents,
           "Registy member cannot see the hidden comment.")


    def test_anon_cannot_see_comments(self):
        comment_text = "You can't see me."
        bug = self._makeBugWithHiddenComment(comment_text)
        view = self.getViewBrowser(context=bug.default_bugtask)
        self.assertFalse(
           comment_text in view.contents,
           "Anonymous person can see the hidden comment.")

    def test_random_cannot_see_comments(self):
        comment_text = "You can't see me."
        bug = self._makeBugWithHiddenComment(comment_text)
        user = self._getUserForTest()
        view = self.getViewBrowser(context=bug.default_bugtask, user=user)
        self.assertFalse(
           comment_text in view.contents,
           "Random user can see the hidden comment.")
