# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webservice unit tests related to Launchpad Questions."""

__metaclass__ = type

from BeautifulSoup import BeautifulSoup
from simplejson import dumps

from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    TestCaseWithFactory,
    celebrity_logged_in,
    )

class TestQuestionRepresentation(TestCaseWithFactory):
    """Test ways of interacting with Question webservice representations."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestQuestionRepresentation, self).setUp() 
        with celebrity_logged_in('admin'):
            self.question = self.factory.makeQuestion(title="This is a question")

        self.webservice = LaunchpadWebServiceCaller(
            'launchpad-library', 'salgado-change-anything')

    def findQuestionDescription(self, response):
        """Find the question title field in an XHTML document fragment."""
        soup = BeautifulSoup(response.body)
        dt = soup.find('dt', text="title").parent
        dd = dt.findNextSibling('dd')
        return str(dd.contents.pop())

    def test_GET_xhtml_representation(self):
        response = self.webservice.get(
            '/%s/+question/%d' % (self.question.target.name,
                self.question.id),
            'application/xhtml+xml')
        self.assertEqual(response.status, 200)

        self.assertEqual(
            self.findQuestionDescription(response),
            "This is a question.")

    def test_PATCH_xhtml_representation(self):
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
            self.findQuestionDescription(response),
            u'<p>See <a href="/questions/%d">question %d</a></p>' % (
            self.question.id, self.question.id))
