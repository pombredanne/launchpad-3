# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webservice unit tests related to Launchpad Bugs."""

__metaclass__ = type

import re
import unittest

from BeautifulSoup import BeautifulSoup
from simplejson import dumps

from zope.component import getMultiAdapter
from lazr.lifecycle.interfaces import IDoNotSnapshot

from lp.bugs.browser.bugtask import get_comments_for_bugtask
from lp.bugs.interfaces.bug import IBug
from canonical.launchpad.ftests import login, logout
from lp.testing import TestCaseWithFactory
from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.launchpad.webapp import snapshot
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import DatabaseFunctionalLayer


class TestBugDescriptionRepresentation(TestCaseWithFactory):
    """Test ways of interacting with Bug webservice representations."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        login('foo.bar@canonical.com')
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
        soup = BeautifulSoup(response.body)
        dt = soup.find('dt', text="description").parent
        dd = dt.findNextSibling('dd')
        return str(dd.contents.pop())

    def test_GET_xhtml_representation(self):
        response = self.webservice.get(
            '/bugs/' + str(self.bug_two.id),
            'application/xhtml+xml')
        self.assertEqual(response.status, 200)

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

        self.assertEqual(response.status, 209)

        self.assertEqual(
            self.findBugDescription(response),
            u'<p>See <a href="/bugs/%d" title="generic">bug %d</a></p>' % (
            self.bug_one.id, self.bug_one.id))


class TestBugCommentRepresentation(TestCaseWithFactory):
    """Test ways of interacting with BugComment webservice representations."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        login('guilherme.salgado@canonical.com ')
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

    def assertRenderedCommentsEqual(self, a_comment, another_comment):
        """Assert that two rendered comments are equal.

        It replaces parts that depend of the current time with fixed
        strings, so that two comments rendered at different times are
        still considered equal.
        """
        when_regexp = re.compile(r'>\d+ .*? ago<')
        a_comment = when_regexp.sub('>WHEN<', a_comment)
        another_comment = when_regexp.sub('>WHEN<', another_comment)
        self.assertEqual(a_comment, another_comment)

    def test_GET_xhtml_representation(self):
        # The XHTML of a BugComment is exactly the same as how it's
        # rendered in the web UI. The existing +box view is re-used to
        # render it.
        response = self.webservice.get(
            self.message_path, 'application/xhtml+xml')

        self.assertEqual(response.status, 200)

        rendered_comment = response.body
        self.assertRenderedCommentsEqual(
            rendered_comment, self.expected_comment_html)


class TestBugMessages(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugMessages, self).setUp('test@canonical.com')
        self.bug = self.factory.makeBug()
        self.message1 = self.factory.makeMessage()
        self.message2 = self.factory.makeMessage(parent=self.message1)
        # Only link message2 to the bug.
        self.bug.linkMessage(self.message2)
        self.webservice = LaunchpadWebServiceCaller(
            'launchpad-library', 'salgado-change-anything')

    def test_messages(self):
        # When one of the messages on a bug is linked to a parent that
        # isn't linked to the bug, the webservice should still return
        # the correct collection link for the bug's messages.
        response = self.webservice.get('/bugs/%d/messages' % self.bug.id)
        self.failUnlessEqual(response.status, 200)
        # The parent_link for the latest message should be None
        # because the parent is not a member of this bug's messages
        # collection itself.
        latest_message = response.jsonBody()['entries'][-1]
        self.failUnlessEqual(self.message2.subject, latest_message['subject'])
        self.failUnlessEqual(None, latest_message['parent_link'])


class TestPostBugWithLargeCollections(TestCaseWithFactory):
    """Ensure that large IBug collections cause OOPSes on POSTs for IBug.

    When a POST request on a bug is processed, a snapshot of the bug
    is created. This can lead to OOPSes as described in bugs 507642,
    505999, 534339: A snapshot of a database collection field is a
    shortlist() copy of the data and the creation of the snapshot fails
    if a collection contains more elements than the hard limit of the
    sortlist().

    Hence we do not include properties in the snapshot that may have
    a large number of elements: messages, bug subscriptions and
    (un)affected users.
    """
    layer = DatabaseFunctionalLayer

    def test_no_snapshots_for_large_collections(self):
        # Ensure that no snapshots are made of the properties comments,
        # bug subscriptions and (un)affected users.
        for field_name in (
            'subscriptions', 'users_affected', 'users_unaffected',
            'users_affected_with_dupes', 'messages'):
            self.failUnless(
                IDoNotSnapshot.providedBy(IBug[field_name]),
                'IBug.%s should not be included in snapshots, see bug 507642.'
                % field_name)

    def test_many_subscribers(self):
        # Many subscriptions do not cause an OOPS for IBug POSTs.
        bug = self.factory.makeBug()
        webservice = LaunchpadWebServiceCaller(
            'launchpad-library', 'salgado-change-anything')
        real_hard_limit_for_snapshot = snapshot.HARD_LIMIT_FOR_SNAPSHOT
        snapshot.HARD_LIMIT_FOR_SNAPSHOT = 3
        try:
            login('foo.bar@canonical.com')
            for count in range(snapshot.HARD_LIMIT_FOR_SNAPSHOT + 1):
                person = self.factory.makePerson()
                bug.subscribe(person, person)
            logout()
            response = webservice.named_post(
                '/bugs/%d' % bug.id, 'subscribe',
                person='http://api.launchpad.dev/beta/~name12')
            self.failUnlessEqual(200, response.status)
        finally:
            snapshot.HARD_LIMIT_FOR_SNAPSHOT = real_hard_limit_for_snapshot


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
