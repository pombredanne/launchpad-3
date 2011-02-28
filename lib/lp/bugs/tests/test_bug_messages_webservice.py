# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webservice unit tests related to Launchpad Bug messages."""

__metaclass__ = type

import transaction

from lazr.restfulclient.errors import HTTPError
from zope.component import getUtility
from zope.security.management import endInteraction

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.interfaces.bugmessage import IBugMessageSet
from lp.registry.interfaces.person import IPersonSet
from lp.testing import (
    launchpadlib_for,
    person_logged_in,
    TestCaseWithFactory,
    )


class TestSetCommentVisibility(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

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
        endInteraction()
        if user is not None:
            lp = launchpadlib_for("test", user)
        else:
            lp = launchpadlib_for("test")

        bug_entry = lp.load(
            'http://api.launchpad.dev/1.0/bugs/%s/' % self.bug.id)
        return bug_entry 

    def _set_visibility(self, bug):
        bug.setCommentVisibility(
            comment_number=1,
            visible=False)

    def assertCommentHidden(self):
        bug_msg_set = getUtility(IBugMessageSet)
        with person_logged_in(self.admin):
            bug_message = bug_msg_set.getByBugAndMessage(
                self.bug, self.message)
            self.assertFalse(bug_message.visible)

    def test_random_user_cannot_set_visible(self):
        nopriv = self.person_set.getByName('no-priv')
        bug = self._get_bug_for_user(nopriv)
        self.assertRaises(
            HTTPError,
            self._set_visibility,
            bug)
        
    def test_anon_cannot_set_visible(self):
        bug = self._get_bug_for_user()
        self.assertRaises(
            HTTPError,
            self._set_visibility,
            bug)

    def test_registry_admin_can_set_visible(self):
        registry = self.person_set.getByName('registry')
        person = self.factory.makePerson()
        with person_logged_in(registry.teamowner):
            registry.addMember(person, registry.teamowner)
        bug = self._get_bug_for_user(person)
        self._set_visibility(bug)
        self.assertCommentHidden()

    def test_admin_can_set_visible(self):
        admins = self.person_set.getByName('admins')
        person = self.factory.makePerson()
        with person_logged_in(admins.teamowner):
            admins.addMember(person, admins.teamowner)
        bug = self._get_bug_for_user(person)
        self._set_visibility(bug)
        self.assertCommentHidden()
