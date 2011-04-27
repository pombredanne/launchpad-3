# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webservice unit tests related to Launchpad Questions."""

__metaclass__ = type

from BeautifulSoup import BeautifulSoup
from lazr.restfulclient.errors import HTTPError
from simplejson import dumps
import transaction
from zope.component import getUtility

from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.person import IPersonSet
from lp.testing import (
    TestCaseWithFactory,
    celebrity_logged_in,
    launchpadlib_for,
    logout,
    person_logged_in,
    ws_object
    )


class TestQuestionRepresentation(TestCaseWithFactory):
    """Test ways of interacting with Question webservice representations."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestQuestionRepresentation, self).setUp()
        with celebrity_logged_in('admin'):
            self.question = self.factory.makeQuestion(
                title="This is a question")

        self.webservice = LaunchpadWebServiceCaller(
            'launchpad-library', 'salgado-change-anything')
        self.webservice.default_api_version = 'devel'

    def findQuestionTitle(self, response):
        """Find the question title field in an XHTML document fragment."""
        soup = BeautifulSoup(response.body)
        dt = soup.find('dt', text="title").parent
        dd = dt.findNextSibling('dd')
        return str(dd.contents.pop())

    def test_top_level_question_get(self):
        # The top level question set can be used via the api to get
        # a question by id via redirect without url hacking.
        response = self.webservice.get(
            '/questions/%s' % self.question.id, 'application/xhtml+xml')
        self.assertEqual(response.status, 200)

    def test_GET_xhtml_representation(self):
        # A question's xhtml representation is available on the api.
        response = self.webservice.get(
            '/%s/+question/%d' % (self.question.target.name,
                self.question.id),
            'application/xhtml+xml')
        self.assertEqual(response.status, 200)

        self.assertEqual(
            self.findQuestionTitle(response),
            "<p>This is a question</p>")

    def test_PATCH_xhtml_representation(self):
        # You can update the question through the api with PATCH.
        new_title = "No, this is a question"

        question_json = self.webservice.get(
            '/%s/+question/%d' % (self.question.target.name,
                self.question.id)).jsonBody()

        response = self.webservice.patch(
            question_json['self_link'],
            'application/json',
            dumps(dict(title=new_title)),
            headers=dict(accept='application/xhtml+xml'))

        self.assertEqual(response.status, 209)

        self.assertEqual(
            self.findQuestionTitle(response),
            "<p>No, this is a question</p>")


class TestSetCommentVisibility(TestCaseWithFactory):
    """Tests who can successfully set comment visibility."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSetCommentVisibility, self).setUp()
        self.person_set = getUtility(IPersonSet)
        admins = self.person_set.getByName('admins')
        self.admin = admins.teamowner
        with person_logged_in(self.admin):
            self.question = self.factory.makeQuestion()
            self.message = self.question.addComment(
                self.admin, 'Some comment')
        transaction.commit()

    def _get_question_for_user(self, user=None):
        """Convenience function to get the api question reference."""
        # End any open lplib instance.
        logout()
        lp = launchpadlib_for("test", user)
        return ws_object(lp, self.question)

    def _set_visibility(self, question):
        """Method to set visibility; needed for assertRaises."""
        question.setCommentVisibility(
            comment_number=0,
            visible=False)

    def test_random_user_cannot_set_visible(self):
        # Logged in users without privs can't set question comment
        # visibility.
        nopriv = self.person_set.getByName('no-priv')
        question = self._get_question_for_user(nopriv)
        self.assertRaises(
            HTTPError,
            self._set_visibility,
            question)

    def test_anon_cannot_set_visible(self):
        # Anonymous users can't set question comment
        # visibility.
        question = self._get_question_for_user()
        self.assertRaises(
            HTTPError,
            self._set_visibility,
            question)

    def test_registry_admin_can_set_visible(self):
        # Members of registry experts can set question comment
        # visibility.
        registry = self.person_set.getByName('registry')
        person = self.factory.makePerson()
        with person_logged_in(registry.teamowner):
            registry.addMember(person, registry.teamowner)
        question = self._get_question_for_user(person)
        self._set_visibility(question)
        self.assertFalse(self.message.visible)

    def test_admin_can_set_visible(self):
        # Admins can set question comment
        # visibility.
        admins = self.person_set.getByName('admins')
        person = self.factory.makePerson()
        with person_logged_in(admins.teamowner):
            admins.addMember(person, admins.teamowner)
        question = self._get_question_for_user(person)
        self._set_visibility(question)
        self.assertFalse(self.message.visible)
