# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Webservice unit tests related to Launchpad Bugs."""

__metaclass__ = type

import unittest

from BeautifulSoup import BeautifulSoup
from simplejson import dumps

from zope.component import getMultiAdapter

from canonical.launchpad.browser.bugtask import get_comments_for_bugtask
from canonical.launchpad.ftests import login
from lp.testing.factory import LaunchpadObjectFactory
from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import DatabaseFunctionalLayer


class TestBugDescriptionRepresentation(unittest.TestCase):
    """Test ways of interacting with Bug webservice representations."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        login('foo.bar@canonical.com')
        self.factory = LaunchpadObjectFactory()
        # Make two bugs, one whose description points to the other, so it will
        # get turned into a HTML link.
        self.bug_one = self.factory.makeBug(title="generic")
        self.bug_two = self.factory.makeBug(
            description="Useless bugs are useless. See Bug %d." % (
            self.bug_one.id))

        self.webservice = LaunchpadWebServiceCaller(
            'launchpad-library', 'salgado-change-anything')

    def findBugDescription(self, response):
        """Find the bug description field in an XHTML document fragment."""
        soup = BeautifulSoup(response.consumeBody())
        dt = soup.find('dt', text="description").parent
        dd = dt.findNextSibling('dd')
        return str(dd.contents.pop())

    def test_GET_xhtml_representation(self):
        response = self.webservice.get(
            '/bugs/' + str(self.bug_two.id),
            'application/xhtml+xml')

        self.assertEqual(response.getStatus(), 200)

        self.assertEqual(
            self.findBugDescription(response),
            u'<p>Useless bugs are useless. '
            'See <a href="/bugs/%d" title="generic">Bug %d</a>.</p>' % (
            self.bug_one.id, self.bug_one.id))

    def test_PATCH_xhtml_representation(self):
        new_description = "See bug %d" % self.bug_one.id

        bug_two_json = self.webservice.get(
            '/bugs/%d' % self.bug_two.id).jsonBody()

        response = self.webservice.patch(
            bug_two_json['self_link'],
            'application/json',
            dumps(dict(description=new_description)),
            headers=dict(accept='application/xhtml+xml'))

        self.assertEqual(response.getStatus(), 209)

        self.assertEqual(
            self.findBugDescription(response),
            u'<p>See <a href="/bugs/%d" title="generic">bug %d</a></p>' % (
            self.bug_one.id, self.bug_one.id))


class TestBugCommentRepresentation(unittest.TestCase):
    """Test ways of interacting with BugComment webservice representations."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        login('guilherme.salgado@canonical.com ')
        self.factory = LaunchpadObjectFactory()
        self.bug = self.factory.makeBug()
        commenter = self.factory.makePerson()
        self.bug.newMessage(
            commenter, 'Comment Subject', 'Comment content')
        comments = get_comments_for_bugtask(self.bug.bugtasks[0])
        self.comment = comments[1]
        comment_view = getMultiAdapter(
            (self.comment, LaunchpadTestRequest()), name="+box")
        self.expected_comment_html = str(comment_view())
        self.message_path = '/%s/+bug/%s/comments/1' % (
                self.bug.bugtasks[0].product.name, self.bug.id)
        self.webservice = LaunchpadWebServiceCaller(
            'launchpad-library', 'salgado-change-anything')

    def test_GET_xhtml_representation(self):
        # The XHTML of a BugComment is exactly the same as how it's
        # rendered in the web UI. The existing +box view is re-used to
        # render it.
        response = self.webservice.get(
            self.message_path, 'application/xhtml+xml')

        self.assertEqual(response.getStatus(), 200)

        rendered_comment = response.consumeBody()
        # XXX Bjorn Tillenius 2009-05-15 bug=377003
        # The current request is a web service request when rendering
        # the HTML, causing canonical_url to produce links pointing to the
        # web service. Adjust the test to compensate for this, and accept
        # that the links will be incorrect for now. We should fix this
        # before using it for anything useful.
        rendered_comment = rendered_comment.replace(
            'http://api.launchpad.dev/beta/',
            'http://launchpad.dev/')
        self.assertEqual(rendered_comment, self.expected_comment_html)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

