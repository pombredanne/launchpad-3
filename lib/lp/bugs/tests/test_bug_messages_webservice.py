# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webservice unit tests related to Launchpad Bug messages."""
from lp.services.features.testing import FeatureFixture

__metaclass__ = type

import transaction

from lazr.restfulclient.errors import HTTPError
from zope.component import getUtility
from zope.security.management import endInteraction
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.interfaces.bugmessage import IBugMessageSet
from lp.registry.interfaces.person import IPersonSet
from lp.testing import (
    launchpadlib_for,
    login_celebrity,
    person_logged_in,
    TestCaseWithFactory,
    WebServiceTestCase,
    )


class TestMessageTraversal(WebServiceTestCase):
    """Tests safe traversal of bugs.

    See bug 607438."""

    def test_message_with_attachments(self):
        bugowner = self.factory.makePerson()
        bug = self.factory.makeBug(owner=bugowner)
        # Traversal over bug messages attachments has no errors.
        expected_messages = []
        with person_logged_in(bugowner):
            for i in range(3):
                att = self.factory.makeBugAttachment(bug)
                expected_messages.append(att.message.subject)

        lp_user = self.factory.makePerson()
        lp_bug = self.wsObject(bug, lp_user)

        attachments = lp_bug.attachments
        messages = [a.message.subject for a in attachments
            if a.message is not None]
        self.assertContentEqual(
            messages,
            expected_messages)


class TestSetCommentVisibility(TestCaseWithFactory):
    """Tests who can successfully set comment visibility."""

    layer = DatabaseFunctionalLayer

    feature_flag = {'disclosure.users_hide_own_bug_comments.enabled': 'on'}

    def setUp(self):
        super(TestSetCommentVisibility, self).setUp()
        self.person_set = getUtility(IPersonSet)
        admins = self.person_set.getByName('admins')
        self.admin = admins.teamowner
        with person_logged_in(self.admin):
            self.bug = self.factory.makeBug()
            self.message = self.factory.makeBugComment(
                bug=self.bug,
                subject='foo',
                body='bar')
        transaction.commit()

    def _get_bug_for_user(self, user=None):
        """Convenience function to get the api bug reference."""
        endInteraction()
        if user is not None:
            lp = launchpadlib_for("test", user)
        else:
            lp = launchpadlib_for("test")

        bug_entry = lp.load('/bugs/%s/' % self.bug.id)
        return bug_entry

    def _set_visibility(self, bug):
        """Method to set visibility; needed for assertRaises."""
        bug.setCommentVisibility(
            comment_number=1,
            visible=False)

    def assertCommentHidden(self):
        bug_msg_set = getUtility(IBugMessageSet)
        with person_logged_in(self.admin):
            bug_message = bug_msg_set.getByBugAndMessage(
                self.bug, self.message)
            self.assertFalse(bug_message.message.visible)

    def test_random_user_cannot_set_visible(self):
        # Logged in users without privs can't set bug comment
        # visibility.
        nopriv = self.person_set.getByName('no-priv')
        bug = self._get_bug_for_user(nopriv)
        self.assertRaises(
            HTTPError,
            self._set_visibility,
            bug)

    def test_anon_cannot_set_visible(self):
        # Anonymous users can't set bug comment
        # visibility.
        bug = self._get_bug_for_user()
        self.assertRaises(
            HTTPError,
            self._set_visibility,
            bug)

    def test_registry_admin_can_set_visible(self):
        # Members of registry experts can set bug comment
        # visibility.
        person = login_celebrity('registry_experts')
        bug = self._get_bug_for_user(person)
        self._set_visibility(bug)
        self.assertCommentHidden()

    def test_admin_can_set_visible(self):
        # Admins can set bug comment
        # visibility.
        person = login_celebrity('admin')
        bug = self._get_bug_for_user(person)
        self._set_visibility(bug)
        self.assertCommentHidden()

    def _test_hide_comment_with_feature_flag(self, person):
        bug = self._get_bug_for_user(person)
        self.assertRaises(
            HTTPError,
            self._set_visibility,
            bug)
        with FeatureFixture(self.feature_flag):
            self._set_visibility(bug)
            self.assertCommentHidden()

    def test_pillar_owner_can_set_visible(self):
        # Pillar owner can set bug comment visibility.
        person = self.factory.makePerson()
        naked_bugtask = removeSecurityProxy(self.bug.default_bugtask)
        removeSecurityProxy(naked_bugtask.pillar).owner = person
        self._test_hide_comment_with_feature_flag(person)

    def test_pillar_driver_can_set_visible(self):
        # Pillar driver can set bug comment visibility.
        person = self.factory.makePerson()
        naked_bugtask = removeSecurityProxy(self.bug.default_bugtask)
        removeSecurityProxy(naked_bugtask.pillar).driver = person
        self._test_hide_comment_with_feature_flag(person)

    def test_pillar_bug_supervisor_can_set_visible(self):
        # Pillar bug supervisor can set bug comment visibility.
        person = self.factory.makePerson()
        naked_bugtask = removeSecurityProxy(self.bug.default_bugtask)
        removeSecurityProxy(naked_bugtask.pillar).bug_supervisor = person
        self._test_hide_comment_with_feature_flag(person)

    def test_pillar_security_contact_can_set_visible(self):
        # Pillar security_contact can set bug comment visibility.
        person = self.factory.makePerson()
        naked_bugtask = removeSecurityProxy(self.bug.default_bugtask)
        removeSecurityProxy(naked_bugtask.pillar).security_contact = person
        self._test_hide_comment_with_feature_flag(person)

    def test_comment_owner_can_set_visible(self):
        # The author of the comment can set bug comment visibility.
        person = self.factory.makePerson()
        removeSecurityProxy(self.message).owner = person
        self._test_hide_comment_with_feature_flag(person)
