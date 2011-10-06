# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugWatch views."""

__metaclass__ = type

from zope.component import getUtility

from lp.services.messages.interfaces.message import IMessageSet
from canonical.testing.layers import LaunchpadFunctionalLayer

from lp.testing import login, login_person, TestCaseWithFactory
from lp.testing.sampledata import ADMIN_EMAIL
from lp.testing.views import create_initialized_view


class TestBugWatchEditView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBugWatchEditView, self).setUp()
        self.person = self.factory.makePerson()

        login_person(self.person)
        self.bug_task = self.factory.makeBug(
            owner=self.person).default_bugtask
        self.bug_watch = self.factory.makeBugWatch(
            bug=self.bug_task.bug)

    def test_cannot_delete_watch_if_linked_to_task(self):
        # It isn't possible to delete a bug watch that's linked to a bug
        # task.
        self.bug_task.bugwatch = self.bug_watch
        view = create_initialized_view(self.bug_watch, '+edit')
        self.assertFalse(
            view.bugWatchIsUnlinked(None),
            "bugWatchIsUnlinked() returned True though there is a task "
            "linked to the watch.")

    def test_cannot_delete_watch_if_linked_to_comment(self):
        # It isn't possible to delete a bug watch that's linked to a bug
        # comment.
        message = getUtility(IMessageSet).fromText(
            "Example message", "With some example content to read.",
            owner=self.person)
        # We need to log in as an admin here as only admins can link a
        # watch to a comment.
        login(ADMIN_EMAIL)
        bug_message = self.bug_watch.addComment('comment-id', message)
        login_person(self.person)
        view = create_initialized_view(self.bug_watch, '+edit')
        self.assertFalse(
            view.bugWatchIsUnlinked(None),
            "bugWatchIsUnlinked() returned True though there is a comment "
            "linked to the watch.")
