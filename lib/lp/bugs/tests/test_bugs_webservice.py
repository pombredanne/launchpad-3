# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webservice unit tests related to Launchpad Bugs."""

__metaclass__ = type

import re

from BeautifulSoup import BeautifulSoup
from lazr.lifecycle.interfaces import IDoNotSnapshot
from lazr.restfulclient.errors import (
    BadRequest,
    HTTPError,
    )
from simplejson import dumps
from storm.store import Store
from testtools.matchers import (
    Equals,
    LessThan,
    )
from zope.component import getMultiAdapter

from canonical.launchpad.ftests import (
    login,
    logout,
    )
from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.launchpad.webapp import snapshot
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.bugs.browser.bugtask import get_comments_for_bugtask
from lp.bugs.interfaces.bug import IBug
from lp.testing import (
    api_url,
    launchpadlib_for,
    TestCaseWithFactory,
    )
from lp.testing._webservice import QueryCollector
from lp.testing.matchers import HasQueryCount
from lp.testing.sampledata import (
    ADMIN_EMAIL,
    USER_EMAIL,
    )


class TestBugConstraints(TestCaseWithFactory):
    """Test constrainsts on bug inputs over the API."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugConstraints, self).setUp()
        product = self.factory.makeProduct(name='foo')
        bug = self.factory.makeBug(product=product)
        lp = launchpadlib_for('testing', product.owner)
        self.bug = lp.bugs[bug.id]

    def _update_bug(self, nick):
        self.bug.name = nick
        self.bug.lp_save()

    def test_numeric_nicknames_fail(self):
        self.assertRaises(
            HTTPError,
            self._update_bug,
            '1.1')

    def test_non_numeric_nicknames_pass(self):
        self._update_bug('bunny')
        self.assertEqual('bunny', self.bug.name)


class TestBugDescriptionRepresentation(TestCaseWithFactory):
    """Test ways of interacting with Bug webservice representations."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        login(ADMIN_EMAIL)
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
            'See <a href="/bugs/%d" class="bug-link">Bug %d</a>.</p>' % (
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
            u'<p>See <a href="/bugs/%d" class="bug-link">bug %d</a></p>' % (
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


class TestBugScaling(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_attachments_query_counts_constant(self):
        # XXX j.c.sackett 2010-09-02 bug=619017
        # This test was being thrown off by the reference bug. To get around
        # the problem, flush and reset are called on the bug storm cache
        # before each call to the webservice. When lp's storm is updated
        # to release the committed fix for this bug, please see about
        # updating this test.
        login(USER_EMAIL)
        self.bug = self.factory.makeBug()
        store = Store.of(self.bug)
        self.factory.makeBugAttachment(self.bug)
        self.factory.makeBugAttachment(self.bug)
        person = self.factory.makePerson()
        webservice = LaunchpadWebServiceCaller(
            'launchpad-library', 'salgado-change-anything')
        collector = QueryCollector()
        collector.register()
        self.addCleanup(collector.unregister)
        url = '/bugs/%d/attachments?ws.size=75' % self.bug.id
        # First request.
        store.flush()
        store.reset()
        response = webservice.get(url)
        self.assertThat(collector, HasQueryCount(LessThan(24)))
        with_2_count = collector.count
        self.failUnlessEqual(response.status, 200)
        login(USER_EMAIL)
        for i in range(5):
            self.factory.makeBugAttachment(self.bug)
        logout()
        # Second request.
        store.flush()
        store.reset()
        response = webservice.get(url)
        self.assertThat(collector, HasQueryCount(Equals(with_2_count)))

    def test_messages_query_counts_constant(self):
        # XXX Robert Collins 2010-09-15 bug=619017
        # This test may be thrown off by the reference bug. To get around the
        # problem, flush and reset are called on the bug storm cache before
        # each call to the webservice. When lp's storm is updated to release
        # the committed fix for this bug, please see about updating this test.
        login(USER_EMAIL)
        bug = self.factory.makeBug()
        store = Store.of(bug)
        self.factory.makeBugComment(bug)
        self.factory.makeBugComment(bug)
        self.factory.makeBugComment(bug)
        person = self.factory.makePerson()
        webservice = LaunchpadWebServiceCaller(
            'launchpad-library', 'salgado-change-anything')
        collector = QueryCollector()
        collector.register()
        self.addCleanup(collector.unregister)
        url = '/bugs/%d/messages?ws.size=75' % bug.id
        # First request.
        store.flush()
        store.reset()
        response = webservice.get(url)
        self.assertThat(collector, HasQueryCount(LessThan(24)))
        with_2_count = collector.count
        self.failUnlessEqual(response.status, 200)
        login(USER_EMAIL)
        for i in range(50):
            self.factory.makeBugComment(bug)
        self.factory.makeBugAttachment(bug)
        logout()
        # Second request.
        store.flush()
        store.reset()
        response = webservice.get(url)
        self.assertThat(collector, HasQueryCount(Equals(with_2_count)))


class TestBugMessages(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugMessages, self).setUp(USER_EMAIL)
        self.bug = self.factory.makeBug()
        self.message1 = self.factory.makeMessage()
        self.message2 = self.factory.makeMessage(parent=self.message1)
        # Only link message2 to the bug.
        self.bug.linkMessage(self.message2)
        self.webservice = launchpadlib_for('launchpad-library', 'salgado')

    def test_messages(self):
        # When one of the messages on a bug is linked to a parent that
        # isn't linked to the bug, the webservice should still include
        # that message in the bug's associated messages.
        bug = self.webservice.load(api_url(self.bug))
        messages = bug.messages
        latest_message = [message for message in messages][-1]
        self.failUnlessEqual(self.message2.subject, latest_message.subject)

        # The parent_link for the latest message should be None
        # because the parent is not a member of this bug's messages
        # collection itself.
        self.failUnlessEqual(None, latest_message.parent)


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
            'users_affected_with_dupes', 'messages', 'attachments',
            'activity'):
            self.failUnless(
                IDoNotSnapshot.providedBy(IBug[field_name]),
                'IBug.%s should not be included in snapshots, see bug 507642.'
                % field_name)

    def test_many_subscribers(self):
        # Many subscriptions do not cause an OOPS for IBug POSTs.
        bug = self.factory.makeBug()

        real_hard_limit_for_snapshot = snapshot.HARD_LIMIT_FOR_SNAPSHOT
        snapshot.HARD_LIMIT_FOR_SNAPSHOT = 3

        webservice = launchpadlib_for('test', 'salgado')
        try:
            login(ADMIN_EMAIL)
            for count in range(snapshot.HARD_LIMIT_FOR_SNAPSHOT + 1):
                person = self.factory.makePerson()
                bug.subscribe(person, person)
            logout()
            lp_bug = webservice.load(api_url(bug))

            # Adding one more subscriber through the web service
            # doesn't cause an OOPS.
            person_to_subscribe = webservice.load('/~name12')
            lp_bug.subscribe(person=person_to_subscribe)
        finally:
            snapshot.HARD_LIMIT_FOR_SNAPSHOT = real_hard_limit_for_snapshot


class TestErrorHandling(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_add_duplicate_bugtask_for_project_gives_bad_request(self):
        bug = self.factory.makeBug()
        product = self.factory.makeProduct()
        bugtask = self.factory.makeBugTask(bug=bug, target=product)

        launchpad = launchpadlib_for('test', bug.owner)
        lp_bug = launchpad.load(api_url(bug))
        exception = self.assertRaises(
            BadRequest, lp_bug.addTask, target=api_url(product))
